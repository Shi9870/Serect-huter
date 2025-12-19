import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pandas as pd
import numpy as np
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Add the parent directory to sys.path to import the utils module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main_function.utils import extract_features

from data_generator import generate_dataset

if __name__ == "__main__":

    # Define the path for the dataset file
    csv_path = os.path.join(os.path.dirname(__file__), 'dataset.csv')
    
    # Check if the dataset exists; if not, generate a new one with 6000 samples
    if not os.path.exists(csv_path):
        df = generate_dataset(6000)
    else:
        # Load the existing dataset
        df = pd.read_csv(csv_path)

        # Ensure the text column is treated as strings to avoid errors
        df['text'] = df['text'].astype(str)

    # Extract features from the text column using the utility function
    # Convert the list of features into a NumPy array for the model
    X = np.array([extract_features(t) for t in df['text']])
    y = df['label'].values

    # Split the data into training (80%) and testing (20%) sets
    # We use sample() for random splitting and keep the indices
    train_indices = df.sample(frac=0.8, random_state=42).index
    
    X_train = X[train_indices]
    y_train = y[train_indices]
    
    # Create the test set by removing the training indices from the dataset
    X_test = np.delete(X, train_indices, axis=0)
    y_test = np.delete(y, train_indices)

    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # Initialize the XGBoost Classifier with specific hyperparameters
    model = xgb.XGBClassifier(
        n_estimators=100,          
        max_depth=4,                
        learning_rate=0.1,        
        eval_metric=["logloss", "error"], 
        use_label_encoder=False    
    )

    # Train the model and monitor performance on both training and test sets
    eval_set = [(X_train, y_train), (X_test, y_test)]
    model.fit(X_train, y_train, eval_set=eval_set, verbose=False)

    # Evaluate the model on the test set
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] # Probability for the positive class
    
    # Calculate and print accuracy
    acc = accuracy_score(y_test, y_pred)
    print("\n" + "="*40)
    print(f"Accuracy: {acc * 100:.2f}%")
    print("="*40)
    
    # Print detailed classification report (Precision, Recall, F1-score)
    print(classification_report(y_test, y_pred))

    # Visualization Setup
    # Create a figure with 3 subplots side by side
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # Plot 1: Learning Curve (Log Loss)
    # Check for overfitting or underfitting
    results = model.evals_result()
    epochs = len(results['validation_0']['logloss'])
    x_axis = range(0, epochs)
    axes[0].plot(x_axis, results['validation_0']['logloss'], label='Train')
    axes[0].plot(x_axis, results['validation_1']['logloss'], label='Test')
    axes[0].legend()
    axes[0].set_title('Log Loss (Learning Curve)')
    axes[0].set_xlabel('Epochs')

    # Plot 2: Feature Importance
    # Define feature names explicitly for the plot
    feature_names = ['Entropy', 'Length', 'Digit Ratio', 'Upper Ratio', 'Symbol Ratio', 'Prefix Score', 'Length Score']
    
    # Assign feature names to the booster object for correct labeling in the plot
    model.get_booster().feature_names = feature_names
    xgb.plot_importance(model, ax=axes[1], height=0.5, importance_type='weight', title='Feature Importance')

    # Plot 3: Confusion Matrix
    # Visualize True Positives, True Negatives, False Positives, and False Negatives
    cm = confusion_matrix(y_test, y_pred)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[2])
    axes[2].set_title('Confusion Matrix')
    axes[2].set_xlabel('Predicted')
    axes[2].set_ylabel('Actual')

    # Adjust layout and display the plots
    plt.tight_layout()
    training_fig = os.path.join(os.path.dirname(__file__), 'training_Outcome.png')
    plt.savefig(training_fig, dpi=300, bbox_inches='tight')
    plt.show()

    # Save the trained model to a JSON file
    # Using the booster object ensures format compatibility
    model_path = os.path.join(os.path.dirname(__file__), 'xgb_model.json')
    model.get_booster().save_model(model_path)
    print(f"Model saved to: {model_path}")
    