import xgboost as xgb
import numpy as np
import os
import re
import sys

# Ensure core.utils can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import extract_features

class MLDetector:
    def __init__(self):
        self.string_pattern = re.compile(r'["\'](.*?)["\']')
        self.model = None

        # Determine current directory and model path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Reconstruct path (assuming 'ml' folder is in the parent directory)
        model_path = os.path.join(current_dir, '..', 'ml', 'xgb_model.json')
        model_path = os.path.abspath(model_path)

        if os.path.exists(model_path):
            try:
                self.model = xgb.Booster()
                self.model.load_model(model_path)
                print("System: Model loaded successfully.")
            except Exception as e:
                print(f"Error: Failed to load model: {e}")
                self.model = None
        else:
            print(f"Error: Model file not found at {model_path}")

    def scan_line(self, line_content, line_num):
        """
        Scans a single line of content and performs ML prediction.
        """
        potential_strings = self.string_pattern.findall(line_content)
        results = []

        for text in potential_strings:
            # 1. Filter short strings (Too short to be a valid key)
            if len(text) < 8 or len(text) > 200:
                continue
            
            # 2. Predict only if model exists
            if self.model:
                try:
                    # Extract features
                    features = np.array([extract_features(text)])
                    
                    # Create XGBoost DMatrix
                    dtest = xgb.DMatrix(features)
                    
                    # Manually assign feature names (Must match training data exactly)
                    dtest.feature_names = ['Entropy', 'Length', 'Digit Ratio', 'Upper Ratio', 'Symbol Ratio', 'Prefix Score', 'Length Score']
                    
                    # Perform prediction
                    prob = self.model.predict(dtest)[0]
                    
                    # 3. Determine Risk Level
                    # Thresholds based on empirical distribution where max scores are ~0.7
                    risk = None

                    # Only report if probability exceeds noise floor (0.15)
                    if prob > 0.15:
                        if prob > 0.65:
                            risk = "CRITICAL" # Highest confidence (e.g., standard AWS patterns)
                        elif prob > 0.45:
                            risk = "HIGH"     # Strong structural match
                        elif prob > 0.35:
                            risk = "MEDIUM"   # Uncertain zone; structurally plausible but low confidence
                        else:
                            risk = "LOW"      # (0.15-0.35) Weak signal, useful for auditing
                    
                        results.append({
                            "line": line_num,
                            "word": text,
                            "score": round(prob * 100, 1),
                            "risk": risk
                        })
                except Exception as e:
                    print(f"Error during prediction: {e}")
            else:
                # Warning if model is not loaded
                print(f"Warning: Potential target '{text}' found, but AI model is not loaded.")
        
        return results