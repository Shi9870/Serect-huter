import xgboost as xgb
import numpy as np
import os
import re
import sys

# 確保可以 import core.utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils import extract_features

class MLDetector:
    def __init__(self):
        self.string_pattern = re.compile(r'["\'](.*?)["\']')
        self.model = None


        
        # --- Debug: 印出目前 detector.py 的位置 ---
        current_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"[DEBUG] detector.py 位於: {current_dir}")

        # 重新組裝路徑 (假設 ml 資料夾在上一層)
        model_path = os.path.join(current_dir, '..', 'ml', 'xgb_model.json')
        # 轉成絕對路徑，方便除錯
        model_path = os.path.abspath(model_path) 
        
        print(f"[DEBUG] 正在嘗試載入模型: {model_path}") # 🔥 關鍵 Debug

        if os.path.exists(model_path):
            try:
                self.model = xgb.Booster()
                self.model.load_model(model_path)
                print("✅ 模型載入成功！")
            except Exception as e:
                print(f"❌ 模型載入發生錯誤: {e}")
                self.model = None
        else:
            print(f"❌ 找不到模型檔案！請確認路徑是否正確")

    def scan_line(self, line_content, line_num):
        """
        掃描單行內容並進行 AI 預測 (已修正特徵名稱問題)
        """
        potential_strings = self.string_pattern.findall(line_content)
        results = []
        
        # 如果這行有內容，印出來確認有讀到 (除錯用，之後可以註解掉)
        # if len(line_content.strip()) > 0:
        #     print(f"[DEBUG-RAW] Line {line_num} 內容: {line_content.strip()}")

        for text in potential_strings:
            # 1. 過濾短字串 (太短不可能是 Key)
            if len(text) < 8 or len(text) > 200:
                # print(f"[DEBUG] Ignored (Length mismatch): '{text}'") 
                continue
            
            # 2. 只有在模型存在時才預測
            if self.model:
                try:
                    # 提取特徵
                    features = np.array([extract_features(text)])
                    
                    # 建立 XGBoost 專用的 DMatrix
                    dtest = xgb.DMatrix(features)
                    
                    # 🔥 [關鍵修正] 手動補上特徵名稱 (必須跟訓練時完全一樣！)

                    dtest.feature_names = ['Entropy', 'Length', 'Digit Ratio', 'Upper Ratio', 'Symbol Ratio', 'Prefix Score', 'Length Score']
                    
                    # 進行預測
                    prob = self.model.predict(dtest)[0]
                    
                    # 印出評分結果 (這行會讓你知道它活著！)
                    print(f"[DEBUG] Analyze: '{text}' => Score: {prob:.4f}")

                    # 3. 判斷風險
                    # Defined thresholds based on empirical distribution where max scores are ~0.7
                    # Logic updated to capture lower-confidence signals as "Low" rather than ignoring them
                    THRESHOLDS = {
                        "Critical": 0.65, # Empirical peak for highest confidence matches
                        "High": 0.45,     # Strong structural match
                        "Medium": 0.25,   # Partial match or lower entropy signal
                        "Low": 0.10       # Weak signal (noise floor), useful for audit logs
                    }

                    risk_level = None

                    if prob > 0.15:
                        if prob > 0.65:
                            risk = "CRITICAL" # Reserved for highest confidence (e.g., standard AWS patterns)
                        elif prob > 0.45:
                            risk = "HIGH"     # Strong structural match, likely valid
                        elif prob > 0.35:
                            risk = "MEDIUM"   # Uncertain zone; structurally plausible but low confidence
                        else:
                            risk = "LOW"      # (0.15-0.35) Reclassified fakes/unknown tokens to reduce alert fatigue
                    
                        results.append({
                            "line": line_num,
                            "word": text,
                            "score": round(prob * 100, 1),
                            "risk": risk
                        })
                except Exception as e:
                    print(f"❌ 預測時發生錯誤: {e}")
            else:
                # 如果沒有模型，印出警告
                print(f"[CRITICAL] 發現潛在目標 '{text}'，但 AI 模型未載入，無法分析！")
        
        return results