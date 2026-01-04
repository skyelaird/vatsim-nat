"""
In-Memory Prediction Tracker
Tracks position prediction accuracy for QA/sanity checking
"""

from datetime import datetime, timedelta, UTC
import math

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in nautical miles"""
    R = 3440.065  # Earth radius in nautical miles
    lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

class PredictionTracker:
    """Track position predictions and validate accuracy"""
    
    def __init__(self):
        self.flights = {}  # callsign -> prediction data
        self.error_threshold_nm = 30  # Flag if error > 30nm
    
    def update(self, flight, trajectory):
        """
        Update predictions for a flight
        
        Args:
            flight: Flight dict with current position
            trajectory: List of trajectory waypoints with ETAs
            
        Returns:
            dict with prediction_error_nm if error detected
        """
        callsign = flight['callsign']
        current_time = datetime.now(UTC)
        
        result = {}
        
        # Calculate error if we have a previous prediction
        if callsign in self.flights:
            prev = self.flights[callsign]
            
            # Calculate time since last prediction
            time_diff = (current_time - prev['prediction_time']).total_seconds() / 60  # minutes
            
            # Only validate if enough time has passed (at least 5 minutes)
            if time_diff >= 5:
                # Calculate actual distance from predicted position
                error_nm = haversine(
                    prev['predicted_lat'], prev['predicted_lon'],
                    flight['lat'], flight['lon']
                )
                
                # Flag if error exceeds threshold
                if error_nm > self.error_threshold_nm:
                    result = {
                        'prediction_suspect': True,
                        'prediction_error_nm': round(error_nm, 1),
                        'time_since_prediction': round(time_diff, 1),
                        'predicted_speed': prev.get('predicted_speed', 0),
                        'actual_speed': flight.get('gs', 0)
                    }
                    # Store error data for get_suspect_flights() to retrieve
                    prev['prediction_error_nm'] = round(error_nm, 1)
                    prev['time_since_prediction'] = round(time_diff, 1)
        
        # Store new prediction if we have a trajectory
        if trajectory and len(trajectory) > 0:
            next_waypoint = trajectory[0]
            
            self.flights[callsign] = {
                'predicted_lat': next_waypoint['lat'],
                'predicted_lon': next_waypoint['lon'],
                'predicted_time': current_time,
                'predicted_speed': flight.get('gs', 0),
                'last_update': current_time
            }
        
        return result
    
    def get_suspect_flights(self):
        """Get list of flights with recent prediction errors"""
        suspect = []
        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        
        for callsign, data in self.flights.items():
            if data['last_update'] > cutoff:
                if data.get('prediction_error_nm', 0) > self.error_threshold_nm:
                    suspect.append({
                        'callsign': callsign,
                        'error_nm': data['prediction_error_nm']
                    })
        
        return suspect
    
    def cleanup(self):
        """Remove flights not seen in 30 minutes"""
        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        self.flights = {
            k: v for k, v in self.flights.items() 
            if v['last_update'] > cutoff
        }
    
    def get_stats(self):
        """Get overall prediction statistics"""
        total = len(self.flights)
        errors = sum(1 for f in self.flights.values() 
                    if f.get('prediction_error_nm', 0) > self.error_threshold_nm)
        
        return {
            'total_tracked': total,
            'flights_with_errors': errors,
            'error_rate': round(errors / total * 100, 1) if total > 0 else 0
        }
