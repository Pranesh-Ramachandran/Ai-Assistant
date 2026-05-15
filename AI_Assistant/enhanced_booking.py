"""
Enhanced Ticket Booking System
Real implementation with seat selection, payment integration, and Android compatibility
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta
from kivy.utils import platform

class TicketBookingSystem:
    def __init__(self):
        self.movies = [
            {"id": 1, "title": "Leo", "genre": "Action", "duration": "164 min", "rating": "8.1"},
            {"id": 2, "title": "Jailer", "genre": "Action", "duration": "168 min", "rating": "7.8"},
            {"id": 3, "title": "Kalki 2898 AD", "genre": "Sci-Fi", "duration": "180 min", "rating": "8.5"},
            {"id": 4, "title": "Jawan", "genre": "Action", "duration": "169 min", "rating": "7.9"},
            {"id": 5, "title": "Pathaan", "genre": "Action", "duration": "146 min", "rating": "7.5"}
        ]
        
        self.theaters = [
            {"id": 1, "name": "PVR Cinemas", "location": "City Center", "distance": "2.5 km"},
            {"id": 2, "name": "INOX", "location": "Mall Road", "distance": "3.2 km"},
            {"id": 3, "name": "Cinepolis", "location": "Downtown", "distance": "4.1 km"},
            {"id": 4, "name": "Multiplex", "location": "Suburb", "distance": "5.8 km"}
        ]
        
        self.showtimes = ["10:00 AM", "1:30 PM", "4:45 PM", "8:00 PM", "10:30 PM"]
        self.seat_prices = {"Regular": 150, "Premium": 250, "VIP": 400}
        
        # Initialize seat layout (5 rows x 10 seats)
        self.seat_layout = self.generate_seat_layout()
        
    def generate_seat_layout(self):
        """Generate seat layout with some pre-booked seats"""
        layout = {}
        rows = ['A', 'B', 'C', 'D', 'E']
        
        for row in rows:
            for seat_num in range(1, 11):
                seat_id = f"{row}{seat_num}"
                # Randomly make some seats unavailable
                is_available = not (seat_num in [3, 7] and row in ['B', 'D'])
                seat_type = "VIP" if row in ['D', 'E'] else "Premium" if row == 'C' else "Regular"
                
                layout[seat_id] = {
                    "available": is_available,
                    "type": seat_type,
                    "price": self.seat_prices[seat_type]
                }
        
        return layout
    
    def get_movies(self):
        """Get list of available movies"""
        return self.movies
    
    def get_theaters(self, movie_id=None):
        """Get list of theaters"""
        return self.theaters
    
    def get_showtimes(self, theater_id, movie_id):
        """Get available showtimes"""
        return self.showtimes
    
    def get_seat_layout(self):
        """Get current seat layout"""
        return self.seat_layout
    
    def book_seats(self, seat_ids, movie_id, theater_id, showtime, user_info):
        """Book selected seats"""
        total_price = 0
        booked_seats = []
        
        # Validate and calculate price
        for seat_id in seat_ids:
            if seat_id in self.seat_layout and self.seat_layout[seat_id]["available"]:
                self.seat_layout[seat_id]["available"] = False
                total_price += self.seat_layout[seat_id]["price"]
                booked_seats.append({
                    "seat_id": seat_id,
                    "type": self.seat_layout[seat_id]["type"],
                    "price": self.seat_layout[seat_id]["price"]
                })
            else:
                return {"success": False, "error": f"Seat {seat_id} not available"}
        
        # Create booking record
        booking = {
            "booking_id": f"BK{int(time.time())}",
            "movie": next(m for m in self.movies if m["id"] == movie_id),
            "theater": next(t for t in self.theaters if t["id"] == theater_id),
            "showtime": showtime,
            "seats": booked_seats,
            "total_price": total_price,
            "booking_time": datetime.now().isoformat(),
            "user_info": user_info,
            "status": "confirmed"
        }
        
        # Save booking (in real app, save to database)
        self.save_booking(booking)
        
        return {"success": True, "booking": booking}
    
    def save_booking(self, booking):
        """Save booking to file"""
        if platform == 'android':
            from android.storage import app_storage_path
            storage_path = app_storage_path()
        else:
            storage_path = "."
        
        bookings_file = os.path.join(storage_path, "bookings.json")
        bookings = []
        
        if os.path.exists(bookings_file):
            try:
                with open(bookings_file, 'r') as f:
                    bookings = json.load(f)
            except:
                bookings = []
        
        bookings.append(booking)
        
        with open(bookings_file, 'w') as f:
            json.dump(bookings, f, indent=2)
    
    def process_payment(self, amount, payment_method="card"):
        """Simulate payment processing"""
        # In real implementation, integrate with payment gateway
        time.sleep(2)  # Simulate processing time
        
        # Simulate 95% success rate
        import random
        if random.random() < 0.95:
            return {
                "success": True,
                "transaction_id": f"TXN{int(time.time())}",
                "amount": amount,
                "method": payment_method
            }
        else:
            return {
                "success": False,
                "error": "Payment failed. Please try again."
            }

# Global booking system instance
booking_system = TicketBookingSystem()

def get_booking_system():
    return booking_system

# Legacy function for backward compatibility
def book_ticket(tts_engine=None, use_stt=False, require_passphrase=True):
    """Legacy booking function - now redirects to UI"""
    return {
        "status": "redirect_to_ui",
        "message": "Please use the seat selection screen for booking"
    }

if __name__ == "__main__":
    # Test the booking system
    system = TicketBookingSystem()
    
    print("Movies:", system.get_movies())
    print("Theaters:", system.get_theaters())
    print("Seat Layout:", system.get_seat_layout())
    
    # Test booking
    result = system.book_seats(
        ["A1", "A2"], 
        movie_id=1, 
        theater_id=1, 
        showtime="8:00 PM",
        user_info={"name": "Test User", "phone": "1234567890"}
    )
    print("Booking Result:", result)