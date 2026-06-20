# JARVIS AI Assistant - Codebase Analysis Report
**Date**: April 13, 2026  
**Scope**: Deep analysis of critical files for bugs, memory leaks, race conditions, and logic errors  
**Analyzed Files**: 
- `jarvis_ai_brain.py` (LLM routing, memory, tool execution)
- `jarvis_grid_server.py` (HTTP server, wake word, TTS threading)
- `neural_grid_ui/index.html` (Animation, state management, API sync)
- `wake_word_detector.py` (Audio capture, wake word detection)
- `stt.py` (Speech recognition, VAD, audio processing)

---

## 🔴 CRITICAL ISSUES (P0 - Fix Immediately)

### Issue #1: Race Condition in SSE Client List Cleanup
**Severity**: CRITICAL  
**File**: [jarvis_grid_server.py](jarvis_grid_server.py#L205-L220)  
**Lines**: 205-220 in `_push_event()`

**Problem**:
```python
def _push_event(event: str, data: dict):
    """Push a server-sent event to all connected clients."""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for client in _sse_clients:
            try:
                client.wfile.write(msg.encode())
                client.wfile.flush()
            except Exception:
                dead.append(client)  # ← RACE: multiple references to dead list
        for c in dead:
            _sse_clients.remove(c)  # ← Can raise ValueError if c removed elsewhere
```

**Root Cause**: 
- The `_sse_clients` list is modified elsewhere (line 231: `_sse_clients.append(self)`) from HTTP handler threads
- Even with `_sse_lock`, the iteration + removal pattern is not atomic
- If one thread modifies list while another iterates, IndexError or ValueError occurs

**Impact**:
- Server crashes with unhandled exception when multiple SSE clients connect/disconnect
- Users lose push notifications (wake word, TTS events)
- Requires manual server restart

**Recommended Fix**:
```python
def _push_event(event: str, data: dict):
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _sse_lock:
        dead = []
        for client in _sse_clients[:]:  # ← Snapshot list first
            try:
                client.wfile.write(msg.encode())
                client.wfile.flush()
            except Exception:
                dead.append(client)
        for c in dead:
            if c in _sse_clients:  # ← Guard removal
                _sse_clients.remove(c)
```

---

### Issue #2: Duplicate Exception Handler Block (Dead Code)
**Severity**: CRITICAL  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L967-L990)  
**Lines**: 967-965 (first `except`) and then lines 977-990 (duplicate `except`)

**Problem**:
```python
    except Exception as exc:
        err = str(exc)
        if "rate_limit" in err.lower() or "429" in err:
            return None
        # tool_use_failed: model tried to call multiple tools as raw text.

    except Exception as exc:  # ← DUPLICATE BLOCK - DEAD CODE
        err = str(exc)
        if "rate_limit" in err.lower() or "429" in err:
            return None
        # tool_use_failed: model tried to call multiple tools as raw text.
        # Retry once without tools so Groq answers directly.
        if "tool_use_failed" in err or "Failed to call a function" in err:
            try:
                r2 = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=msgs,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                record_call("groq")
                return _clean_response(r2.choices[0].message.content or "")
            except Exception as exc2:
                print(f"[Groq retry error] {exc2}")
                return None
        print(f"[Groq error] {exc}")
        return None
```

**Root Cause**: Copy-paste error during refactoring; first `except` catches any Exception, so second block never executes

**Impact**:
- Retry logic for tool_use_failed never executes
- Groq failures always return None instead of attempting recovery
- Loss of robustness for tool-calling edge cases

**Recommended Fix**: Remove lines 977-990 (the duplicate block). Python will only execute the first `except` clause anyway.

---

### Issue #3: Wake Word Listener Restart Without Safe Cleanup
**Severity**: CRITICAL  
**File**: [jarvis_grid_server.py](jarvis_grid_server.py#L227-L246) in `_auto_listen_respond()`  
**Lines**: 235-246

**Problem**:
```python
    finally:
        # Always restart wake listener after responding
        with _wake_lock:
            if _wake_active and WAKE_READY:
                time.sleep(0.1)  # Reduced from 0.3s for faster restart
                try:
                    _wake_system = EfficientWakeWordSystem(wake_phrase="aria")  # ← PROBLEM
                    _wake_system.start(wake_callback=_on_wake_word)
                except Exception as e:
                    print(f"[Wake] Failed to restart: {e}")
```

**Root Cause**:
- Old `_wake_system` still has a `listen_in_background()` thread running
- Creating new instance without stopping the old one causes background thread to compete for microphone
- `_on_wake_word` callback still referenced by old thread; may trigger twice

**Impact**:
- Multiple wake-word listeners consume same mic stream → noisy audio
- Callback fires multiple times for single wake phrase
- Memory leak: old listener threads never fully stop
- CPU usage grows over time

**Recommended Fix**:
```python
    finally:
        # Always restart wake listener after responding
        with _wake_lock:
            if _wake_active and WAKE_READY:
                # CRITICAL: Stop old listener FIRST
                if _wake_system:
                    try:
                        _wake_system.stop()
                    except Exception:
                        pass
                
                time.sleep(0.5)  # Ensure complete thread cleanup
                try:
                    _wake_system = EfficientWakeWordSystem(wake_phrase="aria")
                    _wake_system.start(wake_callback=_on_wake_word)
                except Exception as e:
                    print(f"[Wake] Failed to restart: {e}")
                    _wake_system = None
                    _wake_active = False
```

---

### Issue #4: Conversation Memory File Locking Vulnerability
**Severity**: CRITICAL  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L867-L880) - `_ConversationMemory._save()`  
**Lines**: Multiple instances (640, 761, 430, 767)

**Problem**:
```python
# In _ConversationMemory._save():
def _save(self):
    try:
        with open(self._FILE, "w", encoding="utf-8") as f:
            json.dump({"history": self._history}, f)  # ← NO FILE LOCKING
    except Exception:
        pass

# Concurrent calls from:
# 1. _call_groq() → tool execution → _execute_tool("set_alarm") writes to same file
# 2. _call_gemini() → same
# 3. Local tool calls → same
# 4. FastAPI/asyncio handlers → may call ask() concurrently
```

**Root Cause**:
- Multiple processes/threads can write to `.jarvis_memory.json` simultaneously
- JSON files are not atomic with respect to Python writes
- No exclusion mechanism; partial writes can corrupt JSON structure

**Impact**:
- JSON DecodeError when loading corrupted history
- Missing conversation turns
- Set alarm/preferences get lost randomly
- Cascading failures in `_load()` on next startup

**Recommended Fix**:
```python
import fcntl
import tempfile

class _ConversationMemory:
    def _save(self):
        try:
            # Write to temp file first (atomic rename)
            temp_fd, temp_path = tempfile.mkstemp(suffix='.json', dir=os.path.dirname(self._FILE))
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
                json.dump({"history": self._history}, f)
                fcntl.flock(f, fcntl.LOCK_UN)
            # Atomic rename
            os.replace(temp_path, self._FILE)
        except Exception as e:
            print(f"[Memory] Save failed: {e}")
```

---

### Issue #5: STT listen_in_background Thread Not Fully Stopped
**Severity**: CRITICAL  
**File**: [wake_word_detector.py](wake_word_detector.py#L71-L84)  
**Lines**: 85-88 in `stop()` method

**Problem**:
```python
def stop(self):
    self.is_listening = False
    if self._stop_fn:
        self._stop_fn(wait_for_stop=False)  # ← PROBLEM: wait_for_stop=False
        self._stop_fn = None
    print("[Wake] Stopped.")
```

And in `start()`:
```python
self._stop_fn = self._recognizer.listen_in_background(
    mic, self._audio_callback, phrase_time_limit=1.5  # ← Background thread spawned
)
```

**Root Cause**:
- `listen_in_background()` spawns daemon thread that captures audio and calls `_audio_callback`
- `wait_for_stop=False` returns immediately without joining thread
- Thread continues running in background, competing for microphone with STT during listen phase
- No mechanism to wait for thread to actually finish

**Impact**:
- Audio device kept open even after "stop"
- Battery drain (continuous mic access on mobile)
- Microphone conflicts when switching between wake detection and STT
- Memory grows with uncleaned microphone buffers

**Recommended Fix**:
```python
def stop(self):
    self.is_listening = False
    if self._stop_fn:
        try:
            self._stop_fn(wait_for_stop=True)  # ← Wait for thread to finish
        except Exception as e:
            print(f"[Wake] Stop error: {e}")
        self._stop_fn = None
        time.sleep(0.2)  # Additional buffer to ensure mic fully released
    print("[Wake] Stopped.")
```

---

## 🟠 HIGH PRIORITY ISSUES (P1 - Fix This Week)

### Issue #6: Missing Exception Handling in TTS Callbacks
**Severity**: HIGH  
**File**: [jarvis_grid_server.py](jarvis_grid_server.py#L51-L63) - `_on_tts_started()`, `_on_tts_ended()`  
**Lines**: 51-63

**Problem**:
```python
def _on_tts_started():
    """Called by fast_tts the moment audio begins playing."""
    _push_event("tts_start", {})  # ← Can throw if _sse_clients empty or no lock

def _on_tts_ended():
    """Called by fast_tts when audio playback really ends."""
    global _tts_speaking
    with _tts_lock:
        _tts_speaking = False
    _push_event("tts_done", {})  # ← Unhandled exception
```

**Root Cause**:
- Callbacks invoked from TTS thread (not main thread)
- `_push_event()` assumes clients may be present; if exception occurs, thread dies silently
- No try-except wrapper; threading exception not caught

**Impact**:
- TTS events not delivered to UI
- Grid animation doesn't update state (stays in "thinking" instead of "speaking")
- User thinks system hung while it's actually speaking
- Hard to debug (exceptions in threads are silent)

**Recommended Fix**:
```python
def _on_tts_started():
    try:
        _push_event("tts_start", {})
    except Exception as e:
        print(f"[TTS] Start callback error: {e}")

def _on_tts_ended():
    try:
        global _tts_speaking
        with _tts_lock:
            _tts_speaking = False
        _push_event("tts_done", {})
    except Exception as e:
        print(f"[TTS] End callback error: {e}")
```

---

### Issue #7: LLM Fallback Without Response Validation
**Severity**: HIGH  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L1273-L1295)  
**Lines**: 1283-1295 in `ask()` function

**Problem**:
```python
    # ── 8. Offline fallback ──────────────────────────────────────────────────
    if response is None:
        response = _offline_reply(text)

    response = _clean_response((response or "").strip())  # ← Assumes response is valid
    if response:
        _MEMORY.add_assistant(response)
        # ... caching disabled ...
    return response
```

If both Groq (line 1248) and Gemini (line 1256) return empty string `""` instead of None:

**Root Cause**:
- Check `if response is None` but Groq/Gemini can return `""` (empty string)
- Offline fallback never called for empty responses
- User gets empty reply instead of fallback behavior

**Impact**:
- Responses like "I didn't catch that" or "Server offline" not delivered
- User sees blank chat bubble
- Confusion about whether system is working

**Recommended Fix**:
```python
    # ── 8. Offline fallback ──────────────────────────────────────────────────
    if not response or (isinstance(response, str) and not response.strip()):
        response = _offline_reply(text)

    response = _clean_response((response or "").strip())
    if response:
        _MEMORY.add_assistant(response)
    return response
```

---

### Issue #8: Animation Frame Rate Blocked by API Latency
**Severity**: HIGH  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L1940-L1960) - `send()` function  
**Lines**: 1942-1960

**Problem**:
```javascript
async function send(msg){
    if(!msg.trim()||busy) return;
    busy=true; addMsg('user',msg); setState('thinking');
    const loadEl=addMsg('jarvis','...','loading');
    try{
        const res=await fetch(`${API}/api/chat`,{...});  // ← Blocks animation loop
        const data=await res.json();
        // ... process response ...
        pollTTS();  // ← Synchronous polling
    }catch(e){
        // ...
    }
}
```

**Root Cause**:
- `await fetch()` halts JavaScript execution
- Animation loop (`requestAnimationFrame(loop)`) continues, but no new data to draw
- If server responds slowly (500ms+), canvas gets stale frames

**Impact**:
- Grid animation stutters or appears frozen during API calls
- Poor user experience, feels unresponsive
- Especially bad on slow networks or overloaded server

**Recommended Fix**:
```javascript
async function send(msg){
    if(!msg.trim()||busy) return;
    busy=true; addMsg('user',msg); setState('thinking');
    const loadEl=addMsg('jarvis','...','loading');
    
    // Fire request async, don't await immediately
    (async () => {
        try{
            const res=await fetch(`${API}/api/chat`,{...});
            const data=await res.json();
            const reply=sanitizeReply(data.reply||data.error||'No response.');
            loadEl.remove();
            setState('thinking');  // Important: still show thinking while TTS starts
            addMsg('jarvis',reply);
            if (typeof data.wake_active === 'boolean') setWakeWordUi(data.wake_active);
            pollTTS();
        }catch(e){
            loadEl.remove();
            setState('error');
            addMsg('jarvis','Network error.');
            setTimeout(()=>{setState('idle');busy=false;},2000);
        }
    })();  // Fire and forget; don't block
}
```

---

### Issue #9: Tamil Language Filter Removes Essential Context
**Severity**: HIGH  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L873-L893)  
**Lines**: 873-893 in `_ConversationMemory.get_messages()`

**Problem**:
```python
def get_messages(self, system: str, filter_language: str = None) -> list[dict]:
    result = [{"role": "system", "content": system}]
    
    if filter_language is None:
        result.extend(self._history)
    else:
        # Filter history to only include messages in the same language
        for msg in self._history:
            content = msg.get("content", "")
            has_tamil = any('\u0b80' <= char <= '\u0bff' for char in content)
            
            if filter_language == 'en':
                # Only include English messages (no Tamil script)
                if not has_tamil:
                    result.append(msg)  # ← Removes ALL Tamil messages
            elif filter_language == 'ta':
                if has_tamil or msg.get("role") == "user":
                    result.append(msg)
    
    return result
```

Scenario: User asks in English after previous Tamil question:
1. First query in Tamil → history = `[Tamil user query, Tamil assistant response]`
2. Second query in English → `filter_language='en'`
3. Result: Both Tamil messages filtered out → Lost context

**Root Cause**: Aggressive filtering trades context preservation for language purity

**Impact**:
- Conversation breaks when switching languages
- System loses important context from previous turns
- Replies seem disconnected
- User perceives poor memory/understanding

**Recommended Fix**:
```python
def get_messages(self, system: str, filter_language: str = None) -> list[dict]:
    result = [{"role": "system", "content": system}]
    
    if filter_language is None:
        result.extend(self._history)
    else:
        # Keep recent messages for context continuity, regardless of language
        kept_count = 0
        for msg in reversed(self._history):  # Recent first
            content = msg.get("content", "")
            has_tamil = any('\u0b80' <= char <= '\u0bff' for char in content)
            
            # Always keep last 2 messages for context
            if kept_count < 2 or \
               (filter_language == 'en' and not has_tamil) or \
               (filter_language == 'ta' and has_tamil):
                result.insert(1, msg)  # Insert after system prompt
                kept_count += 1
    
    return result
```

---

### Issue #10: Incomplete Groq JSON Fallback Patterns
**Severity**: HIGH  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L950-L1010)  
**Lines**: 958-1010 in `_call_groq()`

**Problem**:
```python
# Pattern 1: Handles {"name":"...","parameters":{...}}
if response_text.startswith("{") and '"name"' in response_text:
    try:
        tool_call = json.loads(response_text)
        if "name" in tool_call:              # ← Only checks "name" key
            result = _execute_tool(tool_call["name"], tool_call)
            # ...
    except (json.JSONDecodeError, ValueError):  # ← Doesn't catch AttributeError
        pass

# Pattern 2b: Handles get_weather{...}
match = re.match(r'^([a-z_]+)\s*(\{.+\})$', response_text)
if match:
    func_name = match.group(1)
    json_str = match.group(2)
    try:
        args = json.loads(json_str)
        if func_name in ("get_weather", "get_information", ...):
            result = _execute_tool(func_name, args)
            # ...
    except (json.JSONDecodeError, ValueError, AttributeError):  # ← Catches AttributeError here
        pass
```

**Root Cause**:
- Different exception handlers for different patterns
- Pattern 1 doesn't catch AttributeError if `json.loads()` succeeds but structure is wrong
- No validation that args dict contains required keys before calling `_execute_tool()`

**Impact**:
- Tool call silently ignored if JSON malformed
- Tool execution skipped even when intent detected
- User gets generic response instead of tool result

**Recommended Fix**:
```python
# Try all JSON fallback patterns
for func_name, json_str in [
    # Pattern 1: {"name":"get_weather","parameters":{"location":"Kerala"}}
    (match.group(1), match.group(2)) for match in [
        re.search(r'"name"\s*:\s*"([^"]+)".+"(?:parameters|arguments)"\s*:\s*(\{[^}]*\})', response_text)
    ] if match,
    # Pattern 2: get_weather{"location":"Kerala"}
    (m.group(1), m.group(2)) for m in [
        re.match(r'^([a-z_]+)\s*(\{.+\})$', response_text)
    ] if m,
]:
    try:
        args = json.loads(json_str)
        if not isinstance(args, dict):
            continue
        if func_name in VALID_TOOLS:
            result = _execute_tool(func_name, args)
            if result:
                # Synthesize response ...
                return _clean_response(...)
    except (json.JSONDecodeError, ValueError, AttributeError, KeyError) as e:
        print(f"[Groq fallback] Pattern failed: {e}")
        continue
```

---

## 🟡 MEDIUM PRIORITY ISSUES (P2 - Fix This Month)

### Issue #11: Floating Point Blend Not Reset on Rapid State Changes
**Severity**: MEDIUM  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L1730-L1735) - Canvas animation  
**Lines**: 1730-1735 in `setState()`

**Problem**:
```javascript
function setState(s){
    if(s===tgtState) return;
    curState=blend>.5?tgtState:curState;  // ← Uses blend to determine curState
    tgtState=s; 
    blend=0;  // ← Reset blend to 0
    updateUI(s);
}
```

If called twice rapidly (e.g., idle → thinking → idle):
- First call: `curState='idle', tgtState='thinking', blend=0`
- Animation frame increments `blend` to 0.2
- Second call: `curState=(0.2>.5?'thinking':'idle')='idle', tgtState='idle', blend=0`
- Nothing changes; animation already complete

**Root Cause**: Function attempts to smooth state transitions but resets mid-animation

**Impact**:
- Color transitions jittery for rapid state changes
- Visual feedback inconsistent

**Recommended Fix**:
```javascript
function setState(s){
    if(s===tgtState) return;
    // If blend > 0.5, we've committed to target; use it as new current
    if(blend > 0.5) {
        curState = tgtState;
    }
    tgtState = s;
    blend = 0;  // Always reset to start new transition
    updateUI(s);
}
```

---

### Issue #12: Canvas Gradient Created Every Frame Without Cache
**Severity**: MEDIUM  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L1860-L1875) - `drawGrid()` function  
**Lines**: 1860-1875

**Problem**:
```javascript
function drawGrid(state,T,amp){
    // ... setup ...
    for(const d of dots){
        // ... calculate position ...
        if(alpha<.01) continue;
        const g=ctx.createRadialGradient(px,py,0,px,py,radius*4);  // ← NEW GRADIENT EVERY FRAME
        g.addColorStop(0,rgba({r:cr,g:cg,b:cb},alpha*.65));
        g.addColorStop(.45,rgba({r:cr,g:cg,b:cb},alpha*.12));
        g.addColorStop(1,'rgba(0,0,0,0)');
        ctx.fillStyle=g;
        ctx.beginPath();
        ctx.arc(px,py,radius*4,0,Math.PI*2);
        ctx.fill();
        // ... draw solid circle ...
    }
}
```

For a 12×12 grid = 144 dots × 60 FPS = **8,640 gradient objects created per second**

**Root Cause**: No gradient caching; GC pressure builds up

**Impact**:
- Frame rate drops on mobile devices (especially older ones)
- Increased memory usage
- Garbage collection pauses cause visible stutters

**Recommended Fix**:
```javascript
function drawGrid(state,T,amp){
    // ... setup ...
    // Cache for gradients by color to reuse
    const gradientCache = {};
    
    for(const d of dots){
        // ... calculate position ...
        const colKey = `${cr.toFixed(2)},${cg.toFixed(2)},${cb.toFixed(2)},${alpha.toFixed(2)}`;
        
        if(!gradientCache[colKey]) {
            const g = ctx.createRadialGradient(px,py,0,px,py,radius*4);
            g.addColorStop(0, rgba({r:cr,g:cg,b:cb}, alpha*.65));
            g.addColorStop(.45, rgba({r:cr,g:cg,b:cb}, alpha*.12));
            g.addColorStop(1, 'rgba(0,0,0,0)');
            gradientCache[colKey] = g;
        }
        
        ctx.fillStyle = gradientCache[colKey];
        ctx.beginPath();
        ctx.arc(px,py,radius*4,0,Math.PI*2);
        ctx.fill();
    }
}
```

---

### Issue #13: SSE Connection Not Closed Before Reconnect
**Severity**: MEDIUM  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L2140-L2150) - `connectSSE()`  
**Lines**: 2140-2150

**Problem**:
```javascript
(function connectSSE(){
    const es=new EventSource(`${API}/api/events`);  // ← Creates new EventSource
    es.addEventListener('wake',()=>{ /* ... */ });
    // ...
    es.onerror=()=>{ 
        es.close();  // ← Closes in error handler
        setTimeout(connectSSE,5000);  // ← But what if no error?
    };
})();
```

**Root Cause**: If connection succeeds, es.close() never called. If page navigates or server restarts, old connection persists

**Impact**:
- Server keeps old HTTP connections open indefinitely
- Connection count grows
- Server eventually max connections reached
- New clients can't connect

**Recommended Fix**:
```javascript
let sse = null;

function connectSSE(){
    // Close existing connection
    if(sse) { 
        sse.close(); 
        sse = null;
    }
    
    sse = new EventSource(`${API}/api/events`);
    sse.addEventListener('wake',()=>{ /* ... */ });
    sse.addEventListener('wake_state',e=>{ /* ... */ });
    // ... other handlers ...
    
    sse.onerror = () => {
        sse.close();
        sse = null;
        setTimeout(connectSSE, 5000);
    };
}

window.addEventListener('beforeunload', () => {
    if(sse) sse.close();
});

connectSSE();
```

---

### Issue #14: Speech Watchdog Overrides Confirmation Prompts
**Severity**: MEDIUM  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L2020-L2030) - `armSpeechWatchdog()`  
**Lines**: 2020-2030

**Problem**:
```javascript
function armSpeechWatchdog(ms=4500) {
    if (speechWatchdog) clearTimeout(speechWatchdog);
    speechWatchdog = setTimeout(() => {
        if (tgtState === 'speaking') {
            setState('idle');  // ← Unconditional reset
            busy = false;
        }
    }, ms);
}
```

Scenario: Booking confirmation shown while TTS speaks
1. TTS finishes → `_on_tts_ended()` called → `armSpeechWatchdog()`
2. Watchdog fires after 4.5s → `setState('idle')` → resets UI
3. User loses confirmation banner; thinks booking was cancelled

**Root Cause**: Watchdog doesn't check if confirmation banner visible

**Impact**:
- User can't complete booking
- Confirmation timeouts randomly
- Loss of critical confirmations

**Recommended Fix**:
```javascript
function armSpeechWatchdog(ms=4500) {
    if (speechWatchdog) clearTimeout(speechWatchdog);
    speechWatchdog = setTimeout(() => {
        // Don't reset if confirmation banner visible
        const confirmBars = document.querySelectorAll('[id*="confirm-bar"][style*="display: "]');
        const anyConfirming = Array.from(confirmBars).some(bar => 
            getComputedStyle(bar).display !== 'none'
        );
        
        if (tgtState === 'speaking' && !anyConfirming) {
            setState('idle');
            busy = false;
        }
    }, ms);
}
```

---

### Issue #15: VAD Mode Not Applied to Existing Instance
**Severity**: MEDIUM  
**File**: [stt.py](stt.py#L359-L365) - `set_vad_sensitivity()`  
**Lines**: 359-365

**Problem**:
```python
_VAD = _webrtcvad.Vad(2)  # ← Mode set to 2 during init

def set_vad_sensitivity(value: int):
    os.environ["JARVIS_VAD_SENSITIVITY"] = str(max(0, min(100, int(value))))
    if _VAD_OK and _VAD:
        mode = 3 if value >= 75 else 2 if value >= 50 else 1 if value >= 25 else 0
        _VAD.set_mode(mode)  # ← Calls set_mode() on existing VAD
```

But: `_VAD` was created with mode 2 in `__init__`. After first `listen()` call, mode is locked to 2.

**Root Cause**: `set_vad_sensitivity()` calls after VAD already initialized; mode change doesn't propagate to running frames

**Impact**:
- Voice detection threshold can't be adjusted after first use
- Setting is ignored post-initialization

**Recommended Fix**:
```python
def set_vad_sensitivity(value: int):
    try:
        os.environ["JARVIS_VAD_SENSITIVITY"] = str(max(0, min(100, int(value))))
        if _VAD_OK:
            mode = 3 if value >= 75 else 2 if value >= 50 else 1 if value >= 25 else 0
            if _VAD:
                _VAD.set_mode(mode)  # Only call if VAD exists
            _VAD = _webrtcvad.Vad(mode)  # Recreate if not exists
    except Exception as e:
        print(f"[VAD] Sensitivity update failed: {e}")
```

---

### Issue #16: No Request Deduplication in UI
**Severity**: MEDIUM  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html) - Multiple button handlers  
**Lines**: Button event listeners throughout

**Problem**:
```javascript
// User can spam buttons:
// Mic button → /api/listen
// Mic button (again) → /api/listen (NEW request while first still pending)
// Result: TTS queues 2 responses; user hears audio twice

document.getElementById('mb').addEventListener('click',async()=>{
    if(micActive) return;  // ← Only checks flag, not pending request
    micActive=true;
    // ... fetch /api/listen ...
    // ... SLOW network: takes 5 seconds ...
    // User clicks again while waiting → micActive still true → correctly blocked
    // BUT: if first request fails, flag not reset properly
});
```

**Root Cause**: 
- Single `busy` flag for all requests
- No tracking of which requests are in-flight
- Button spam can queue multiple identical API calls

**Impact**:
- TTS speaks multiple times for single query
- Booking requests duplicated
- Confusion for user

**Recommended Fix**:
```javascript
const pendingRequests = new Map();  // Track pending requests

function withDedup(endpointKey, requestFn) {
    if (pendingRequests.has(endpointKey)) {
        console.log(`[Dedup] ${endpointKey} already pending`);
        return pendingRequests.get(endpointKey);
    }
    
    const promise = Promise.resolve()
        .then(requestFn)
        .finally(() => pendingRequests.delete(endpointKey));
    
    pendingRequests.set(endpointKey, promise);
    return promise;
}

// Usage:
document.getElementById('mb').addEventListener('click', async() => {
    if(micActive) return;
    micActive = true;
    await withDedup('api/listen', async () => {
        const res = await fetch(`${API}/api/listen`, {...});
        // ... handle response ...
    });
    micActive = false;
});
```

---

## 🔵 LOW PRIORITY ISSUES (P3 - Nice to Have)

### Issue #17: Conversation History Rebuilt Every LLM Call
**Severity**: LOW (Performance)  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L1232-L1235) - Line 1232 in `ask()` function

Performance issue: `get_messages()` rebuilds filtered history every call instead of caching. For a 160-turn history with language filter, this is O(160) overhead per call.

### Issue #18: Emotion Adapter Code Disabled But Not Removed
**Severity**: LOW (Technical Debt)  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L1283-L1291)  

Dead import and disabled code block. Should be either removed or re-enabled with proper testing.

### Issue #19: Response Caching Disabled (Stale Response Risk)
**Severity**: LOW (Feature)  
**File**: [jarvis_ai_brain.py](jarvis_ai_brain.py#L1289-L1293)

Caching disabled due to previous Tamil response staling issue. Should use `(clean_text, detected_lang)` tuple as key to cache language-aware.

### Issue #20: Hardcoded Grid Geometry Constants
**Severity**: LOW (UX)  
**File**: [neural_grid_ui/index.html](neural_grid_ui/index.html#L1720-L1721)

`COLS=12, ROWS=12` hardcoded; should scale based on canvas size for responsive design.

---

## Summary & Recommendations

| Severity | Count | Fix Time | Impact |
|----------|-------|----------|--------|
| CRITICAL | 5 | ~4-6 hours | Core stability, data integrity, threading |
| HIGH | 5 | ~6-8 hours | Robustness, state management, fallbacks |
| MEDIUM | 6 | ~8-10 hours | Performance, UX polish |
| LOW | 4 | ~4-5 hours | Technical debt, optimization |
| **TOTAL** | **20** | **~22-29 hours** | **Comprehensive quality improvement** |

### Recommended Fix Priority Order:
1. **#4** (file locking) - Prevents data corruption
2. **#1** (SSE race) - Prevents server crashes
3. **#5** (wake thread) - Fixes battery drain + mic conflicts
4. **#3** (wake restart) - Fixes zombie threads
5. **#2** (duplicate except) - Remove dead code
6. **#6, #7, #10** (exception handling) - Robustness
7. **#8, #9, #13, #14** (UI/animation) - User experience
8. **#11, #12, #15, #16** (performance) - Optimization
9. **#17-20** (technical debt) - Code quality

All critical issues should be fixed before next major release.

