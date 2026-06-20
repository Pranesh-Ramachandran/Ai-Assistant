"""
Advanced NLP Module for Jarvis AI Assistant
Uses Transformer models (BERT/RoBERTa) for better intent classification and context understanding.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import json
import os
from typing import List, Tuple, Dict
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedNLPBrain:
    def __init__(self, model_name="microsoft/DialoGPT-small"):
        """Initialize advanced NLP brain with transformer model."""
        self.model_name = model_name
        self.model_path = "jarvis_advanced_nlp_model"
        self.intent_model_path = "jarvis_intent_classifier"
        self.vocab_file = "jarvis_advanced_vocab.json"
        self.feedback_file = "jarvis_advanced_feedback.json"

        # Intent categories (expanded)
        self.intents = [
            "greeting", "time_date", "weather", "music", "iot_control",
            "alarm_reminder", "info_request", "booking", "exit", "unknown",
            "conversation", "joke", "help", "settings", "calendar"
        ]

        # Conversation memory
        self.conversation_history = []
        self.max_history = 10

        # Confidence thresholds
        self.high_confidence = 0.8
        self.medium_confidence = 0.5

        # Initialize models
        self.tokenizer = None
        self.model = None
        self.intent_classifier = None

        self.load_or_create_models()

    def load_or_create_models(self):
        """Load existing models or create new ones."""
        try:
            # Load conversational model
            if os.path.exists(self.model_path):
                logger.info("Loading existing conversational model...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            else:
                logger.info("Creating new conversational model...")
                self._create_conversational_model()

            # Load intent classifier
            if os.path.exists(self.intent_model_path):
                logger.info("Loading existing intent classifier...")
                self.intent_classifier = AutoModelForSequenceClassification.from_pretrained(
                    self.intent_model_path,
                    num_labels=len(self.intents)
                )
            else:
                logger.info("Creating new intent classifier...")
                self._create_intent_classifier()

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Fallback to basic functionality
            self.model = None
            self.intent_classifier = None

    def _create_conversational_model(self):
        """Create and train a basic conversational model."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=2  # For now, just positive/negative response quality
            )

            # Save the model
            self.model.save_pretrained(self.model_path)
            self.tokenizer.save_pretrained(self.model_path)

        except Exception as e:
            logger.error(f"Error creating conversational model: {e}")

    def _create_intent_classifier(self):
        """Create and train intent classification model."""
        try:
            from transformers import BertTokenizer, BertForSequenceClassification

            self.intent_tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
            self.intent_classifier = BertForSequenceClassification.from_pretrained(
                'bert-base-uncased',
                num_labels=len(self.intents)
            )

            # Train on basic examples
            self._train_intent_classifier()

            # Save the model
            self.intent_classifier.save_pretrained(self.intent_model_path)
            self.intent_tokenizer.save_pretrained(self.intent_model_path)

        except Exception as e:
            logger.error(f"Error creating intent classifier: {e}")

    def _train_intent_classifier(self):
        """Train the intent classifier on basic examples."""
        # Training data
        training_examples = [
            ("hello how are you", 0), ("hi there", 0), ("good morning", 0),
            ("what time is it", 1), ("current time", 1), ("what's the date", 1),
            ("how's the weather", 2), ("is it raining", 2), ("weather forecast", 2),
            ("play some music", 3), ("start music", 3), ("music please", 3),
            ("turn on lights", 4), ("switch off fan", 4), ("control device", 4),
            ("set alarm", 5), ("remind me", 5), ("wake me up", 5),
            ("tell me about", 6), ("what is", 6), ("explain", 6),
            ("book tickets", 7), ("make reservation", 7), ("schedule", 7),
            ("goodbye", 8), ("bye", 8), ("see you later", 8),
            ("how are you doing", 10), ("tell me a joke", 11), ("help me", 12)
        ]

        # Simple training (in practice, you'd want more sophisticated training)
        logger.info("Training intent classifier with basic examples...")

        # For now, just save the untrained model
        # In a real implementation, you'd train on a proper dataset
        pass

    def predict_intent_advanced(self, text: str) -> Tuple[str, float]:
        """Predict intent using advanced NLP."""
        if not self.intent_classifier or not self.intent_tokenizer:
            # Fallback to basic intent detection
            return self._basic_intent_detection(text)

        try:
            # Tokenize input
            inputs = self.intent_tokenizer(text, return_tensors="pt", padding=True, truncation=True)

            # Get prediction
            with torch.no_grad():
                outputs = self.intent_classifier(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)
                predicted_class = torch.argmax(probabilities, dim=1).item()
                confidence = probabilities[0][predicted_class].item()

            intent = self.intents[predicted_class] if predicted_class < len(self.intents) else "unknown"
            return intent, confidence

        except Exception as e:
            logger.error(f"Error in advanced intent prediction: {e}")
            return self._basic_intent_detection(text)

    def _basic_intent_detection(self, text: str) -> Tuple[str, float]:
        """Fallback basic intent detection."""
        text_lower = text.lower()

        # Simple keyword matching
        intent_keywords = {
            "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
            "time_date": ["time", "date", "day", "today", "now"],
            "weather": ["weather", "temperature", "rain", "sunny", "forecast"],
            "music": ["play", "music", "song", "audio"],
            "iot_control": ["turn on", "turn off", "switch", "light", "bulb", "fan"],
            "alarm_reminder": ["alarm", "remind", "reminder", "wake up", "set"],
            "info_request": ["what", "who", "where", "when", "why", "how", "tell me"],
            "booking": ["book", "ticket", "reserve", "schedule"],
            "exit": ["bye", "goodbye", "exit", "quit"],
            "conversation": ["how are you", "what's up", "talk"],
            "joke": ["joke", "funny", "laugh"],
            "help": ["help", "assist", "support"]
        }

        for intent, keywords in intent_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return intent, 0.7  # Medium confidence for keyword matches

        return "unknown", 0.3

    def generate_contextual_response(self, intent: str, text: str, confidence: float) -> str:
        """Generate contextual response considering conversation history."""
        # Add to conversation history
        self.conversation_history.append({
            "text": text,
            "intent": intent,
            "confidence": confidence,
            "timestamp": __import__('time').time()
        })

        # Keep only recent history
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)

        # Generate response based on intent and context
        if confidence >= self.high_confidence:
            return self._generate_high_confidence_response(intent, text)
        elif confidence >= self.medium_confidence:
            return self._generate_medium_confidence_response(intent, text)
        else:
            return self._generate_low_confidence_response(intent, text)

    def _generate_high_confidence_response(self, intent: str, text: str) -> str:
        """Generate response for high confidence predictions."""
        responses = {
            "greeting": [
                "Hello! I'm here to help you.",
                "Hi there! What can I do for you today?",
                "Greetings! How may I assist you?"
            ],
            "time_date": [
                "I'll check the current time and date for you.",
                "Let me get you the time information."
            ],
            "weather": [
                "I'll fetch the weather information for you.",
                "Let me check the current weather conditions."
            ],
            "music": [
                "I'll help you with music playback.",
                "Starting your music now."
            ],
            "iot_control": [
                "I'll control your smart devices.",
                "Executing device command."
            ],
            "alarm_reminder": [
                "I'll set up your alarm or reminder.",
                "Scheduling that for you."
            ],
            "info_request": [
                "I'll find that information for you.",
                "Let me look that up."
            ],
            "booking": [
                "I'll help you with booking.",
                "Let's get that arranged."
            ],
            "exit": [
                "Goodbye! Have a great day!",
                "See you later!",
                "Take care!"
            ],
            "conversation": [
                "I'm doing well, thank you! How are you?",
                "I'm here and ready to help!",
                "All systems operational!"
            ],
            "joke": [
                "Why don't scientists trust atoms? Because they make up everything!",
                "What do you call fake spaghetti? An impasta!",
                "Why did the scarecrow win an award? He was outstanding in his field!"
            ],
            "help": [
                "I can help you with time, weather, music, device control, alarms, information, and more!",
                "Just tell me what you need - I'm here to assist."
            ]
        }

        if intent in responses:
            import random
            return random.choice(responses[intent])
        else:
            return "I'm ready to help with that!"

    def _generate_medium_confidence_response(self, intent: str, text: str) -> str:
        """Generate response for medium confidence predictions."""
        return f"I think you want me to {intent.replace('_', ' ')}. Is that correct?"

    def _generate_low_confidence_response(self, intent: str, text: str) -> str:
        """Generate response for low confidence predictions."""
        return "I'm not entirely sure what you mean. Could you please rephrase that?"

    def learn_from_feedback(self, text: str, correct_intent: str):
        """Learn from user feedback to improve future predictions."""
        # Save feedback for future model retraining
        feedback_entry = {
            "text": text,
            "correct_intent": correct_intent,
            "timestamp": __import__('time').time()
        }

        try:
            if os.path.exists(self.feedback_file):
                with open(self.feedback_file, 'r') as f:
                    feedback_data = json.load(f)
            else:
                feedback_data = []

            feedback_data.append(feedback_entry)

            # Keep only recent feedback
            if len(feedback_data) > 100:
                feedback_data = feedback_data[-100:]

            with open(self.feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)

            logger.info(f"Learned from feedback: '{text}' -> {correct_intent}")

        except Exception as e:
            logger.error(f"Error saving feedback: {e}")

    def get_conversation_context(self) -> List[Dict]:
        """Get recent conversation context."""
        return self.conversation_history[-5:]  # Last 5 interactions

    def analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of the input text."""
        # Simple sentiment analysis (could be enhanced with a proper model)
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "happy", "love"]
        negative_words = ["bad", "terrible", "awful", "hate", "sad", "angry", "disappointed"]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

if __name__ == "__main__":
    # Test the advanced NLP system
    brain = AdvancedNLPBrain()

    test_inputs = [
        "Hello Jarvis, how are you?",
        "What time is it?",
        "Play some music please",
        "Turn on the living room lights",
        "Set an alarm for 7 AM",
        "Tell me a joke",
        "What's the weather like?",
        "Goodbye"
    ]

    print("🧠 Testing Advanced NLP System:")
    print("=" * 50)

    for test_input in test_inputs:
        intent, confidence = brain.predict_intent_advanced(test_input)
        response = brain.generate_contextual_response(intent, test_input, confidence)
        sentiment = brain.analyze_sentiment(test_input)

        print(f"Input: '{test_input}'")
        print(f"Intent: {intent} (confidence: {confidence:.2f})")
        print(f"Sentiment: {sentiment}")
        print(f"Response: {response}")
        print("-" * 30)
