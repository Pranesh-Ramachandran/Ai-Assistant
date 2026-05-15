"""
Offline Entertainment - Fun activities when internet is unavailable
Games, riddles, and companionship features for offline times
"""

import random
from typing import List, Dict, Optional

class OfflineEntertainment:
    def __init__(self):
        self.riddles = [
            {"question": "I speak without a mouth and hear without ears. What am I?", "answer": "echo"},
            {"question": "What has keys but no locks, space but no room?", "answer": "keyboard"},
            {"question": "I'm tall when young, short when old. What am I?", "answer": "candle"},
            {"question": "What gets wet while drying?", "answer": "towel"},
            {"question": "What has hands but cannot clap?", "answer": "clock"}
        ]
        
        self.tamil_riddles = [
            {"question": "வாயில்லாமல் பேசுவேன், காதில்லாமல் கேட்பேன். நான் யார்?", "answer": "எதிரொலி"},
            {"question": "தலையில்லாமல் தொப்பி அணிவேன். நான் என்ன?", "answer": "ஆணி"},
            {"question": "கால்கள் இல்லாமல் ஓடுவேன். நான் என்ன?", "answer": "நதி"}
        ]
        
        self.jokes = [
            "Why don't scientists trust atoms? Because they make up everything!",
            "What do you call a bear with no teeth? A gummy bear!",
            "Why did the math book look so sad? Because it had too many problems!"
        ]
        
        self.motivational_quotes = [
            "Every moment is a fresh beginning.",
            "Believe you can and you're halfway there.",
            "The only impossible journey is the one you never begin.",
            "Success is not final, failure is not fatal: it is the courage to continue that counts."
        ]
        
        self.tongue_twisters = [
            "She sells seashells by the seashore.",
            "How much wood would a woodchuck chuck if a woodchuck could chuck wood?",
            "Red leather, yellow leather.",
            "Unique New York, unique New York."
        ]
        
        self.number_game_target = None
        self.number_game_attempts = 0
        self.current_riddle = None
    
    def start_number_guessing_game(self) -> str:
        """Start a number guessing game"""
        self.number_game_target = random.randint(1, 100)
        self.number_game_attempts = 0
        return "I'm thinking of a number between 1 and 100. Can you guess it?"
    
    def process_number_guess(self, guess: int) -> str:
        """Process a guess in the number game"""
        if self.number_game_target is None:
            return self.start_number_guessing_game()
        
        self.number_game_attempts += 1
        
        if guess == self.number_game_target:
            attempts = self.number_game_attempts
            self.number_game_target = None
            return f"Correct! You got it in {attempts} attempts. Well done! 🎉"
        elif guess < self.number_game_target:
            return "Too low! Try a higher number."
        else:
            return "Too high! Try a lower number."
    
    def get_random_riddle(self, language: str = 'english') -> str:
        """Get a random riddle"""
        if language.lower() == 'tamil':
            riddle = random.choice(self.tamil_riddles)
        else:
            riddle = random.choice(self.riddles)
        
        self.current_riddle = riddle
        return f"Here's a riddle: {riddle['question']}"
    
    def check_riddle_answer(self, answer: str) -> str:
        """Check if riddle answer is correct"""
        if not self.current_riddle:
            return "No riddle is active right now."
        
        if answer.lower().strip() == self.current_riddle['answer'].lower():
            self.current_riddle = None
            return "Correct! Well done! 🎉"
        else:
            return "Not quite right. Want to try again or hear the answer?"
    
    def get_riddle_answer(self) -> str:
        """Reveal the current riddle answer"""
        if not self.current_riddle:
            return "No riddle is active."
        
        answer = self.current_riddle['answer']
        self.current_riddle = None
        return f"The answer is: {answer}"
    
    def get_random_joke(self) -> str:
        """Get a random joke"""
        return random.choice(self.jokes)
    
    def get_motivational_quote(self) -> str:
        """Get a motivational quote"""
        return random.choice(self.motivational_quotes)
    
    def get_tongue_twister(self) -> str:
        """Get a tongue twister challenge"""
        twister = random.choice(self.tongue_twisters)
        return f"Try saying this fast: {twister}"
    
    def start_math_quiz(self) -> str:
        """Start a simple math quiz"""
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        operation = random.choice(['+', '-', '*'])
        
        if operation == '+':
            answer = num1 + num2
        elif operation == '-':
            answer = num1 - num2
        else:  # multiplication
            answer = num1 * num2
        
        self.math_answer = answer
        return f"Quick math: {num1} {operation} {num2} = ?"
    
    def check_math_answer(self, answer: int) -> str:
        """Check math quiz answer"""
        if not hasattr(self, 'math_answer'):
            return "No math question is active."
        
        if answer == self.math_answer:
            delattr(self, 'math_answer')
            return "Correct! Great job! 🎉"
        else:
            correct = self.math_answer
            delattr(self, 'math_answer')
            return f"Not quite. The answer was {correct}."
    
    def handle_offline_request(self, request: str) -> Optional[str]:
        """Handle entertainment requests when offline"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['riddle', 'puzzle']):
            return self.get_random_riddle()
        elif any(word in request_lower for word in ['joke', 'funny']):
            return self.get_random_joke()
        elif any(word in request_lower for word in ['quote', 'motivation', 'inspire']):
            return self.get_motivational_quote()
        elif any(word in request_lower for word in ['tongue twister', 'twister']):
            return self.get_tongue_twister()
        elif any(word in request_lower for word in ['number', 'guess', 'game']):
            return self.start_number_guessing_game()
        elif any(word in request_lower for word in ['math', 'calculate', 'quiz']):
            return self.start_math_quiz()
        elif 'bored' in request_lower:
            activities = [
                "Want to try a riddle?",
                "How about a number guessing game?",
                "I can tell you a joke!",
                "Want to hear a motivational quote?",
                "Try a tongue twister challenge?"
            ]
            return random.choice(activities)
        
        return None

# Global instance
offline_entertainment = OfflineEntertainment()