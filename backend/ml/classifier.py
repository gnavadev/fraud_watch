import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_recall_curve, auc
from sklearn.preprocessing import StandardScaler
import joblib

class FraudClassifier:
    def __init__(self):
        # 'balanced' class_weight handles the imbalanced data (the 1% fraud cases)
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()

    def train(self, df: pd.DataFrame, target_col='is_fraud'):
        """
        Full training pipeline: Scaling -> Train/Test Split -> Random Forest
        """
        print("Starting training pipeline...")
        
        # Feature separation
        X = df.drop(columns=[target_col])
        y = df[target_col]

        # Stratified Split (Crucial for fraud data)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        # Scale Data
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        self._evaluate(X_test_scaled, y_test)
        
        return self.model

    def _evaluate(self, X_test, y_test):
        # Predict probabilities for AUPRC calculation
        probs = self.model.predict_proba(X_test)[:, 1]
        precision, recall, _ = precision_recall_curve(y_test, probs)
        auprc = auc(recall, precision)
        
        print(f"Model Training Complete.")
        print(f"AUPRC (Area Under Precision-Recall Curve): {auprc:.4f}")
        
    def predict(self, new_data: pd.DataFrame):
        scaled_data = self.scaler.transform(new_data)
        return self.model.predict(scaled_data)

    def save_model(self, path='model.pkl'):
        joblib.dump(self.model, path)