"""One-time bulk seed script: writes a 5-question module quiz for every
module of the "Artificial Intelligence" (10 modules) and "Machine Learning"
(9 modules) courses — 19 quizzes / 95 questions total, matched to each
module's actual lesson content.

HOW TO RUN (from your own computer, same as seed_ai_course.py / seed_ml_course.py):

    pip install pymongo
    export MONGO_URI="mongodb+srv://karkavelrajaj_db_user:YOUR_PASSWORD@cluster0.ua3bzky.mongodb.net/?retryWrites=true&w=majority"
    python seed_quizzes.py

SAFE TO RE-RUN: it upserts by module title (looked up the same way
seed_ai_course.py / seed_ml_course.py look up modules), so running it
twice just replaces each quiz's 5 questions rather than creating
duplicates. It does NOT touch courses, modules, or lessons — those must
already exist (i.e. run seed_ai_course.py / seed_ml_course.py first, if
you haven't already).

Each question is single-answer MCQ, multi-select, or true/false — no
short-answer, matching the "auto-graded only" design of the module quiz
feature. Every question has exactly one correct answer for
single/true_false types, or 2+ for multi-select.
"""

import os
import sys

from pymongo import MongoClient
from pymongo.server_api import ServerApi

MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = os.environ.get("DB_NAME", "dsiar_lms_v2")

if not MONGO_URI:
    print("ERROR: set the MONGO_URI environment variable first.")
    sys.exit(1)

client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
db = client[DB_NAME]


def q(qid, qtype, text, options, correct_texts):
    """options: list of option text strings. correct_texts: the subset of
    `options` (by exact text) that are correct."""
    opts = [{"id": f"o{i + 1}", "text": t} for i, t in enumerate(options)]
    correct_ids = [o["id"] for o in opts if o["text"] in correct_texts]
    assert correct_ids, f"{qid}: no correct option matched in {text!r}"
    if qtype in ("single", "true_false"):
        assert len(correct_ids) == 1, f"{qid}: single/true_false needs exactly 1 correct option"
    return {"id": qid, "type": qtype, "text": text, "options": opts, "correct_option_ids": correct_ids}


def tf(qid, text, correct: bool):
    return q(qid, "true_false", text, ["True", "False"], ["True" if correct else "False"])


def five(*questions):
    assert len(questions) == 5, f"expected exactly 5 questions, got {len(questions)}"
    for i, question in enumerate(questions):
        question["id"] = f"q{i + 1}"
    return list(questions)


# =============================================================================
# ARTIFICIAL INTELLIGENCE — 10 modules
# =============================================================================

AI_QUIZZES = {
    "Introduction to AI": five(
        q("q1", "single", "Which of these best defines Artificial Intelligence?",
          ["A fixed set of if-else rules only", "The simulation of human intelligence processes by machines", "A type of database", "A programming language"],
          ["The simulation of human intelligence processes by machines"]),
        q("q2", "multi", "Which of these are commonly considered subfields of AI?",
          ["Machine Learning", "Natural Language Processing", "Computer Vision", "Spreadsheet formatting"],
          ["Machine Learning", "Natural Language Processing", "Computer Vision"]),
        tf("q3", "AI systems can only follow rules explicitly programmed by a human, and can never learn from data.", False),
        q("q4", "single", "Which is an example of a real-world AI application?",
          ["A calculator adding two numbers", "A spam filter that learns to detect junk email", "A static HTML webpage", "A basic file compression tool"],
          ["A spam filter that learns to detect junk email"]),
        tf("q5", "AI, Machine Learning, and Deep Learning are all exactly the same thing with no differences.", False),
    ),
    "Python for AI": five(
        q("q1", "single", "Which Python library is most commonly used for numerical array operations in AI/ML?",
          ["NumPy", "Flask", "Django", "BeautifulSoup"],
          ["NumPy"]),
        q("q2", "single", "Which Python library is the standard choice for tabular data manipulation (rows/columns, like a spreadsheet)?",
          ["Pandas", "Matplotlib", "Requests", "Pillow"],
          ["Pandas"]),
        q("q3", "multi", "Which of these are common data preprocessing steps before feeding data into a model?",
          ["Handling missing values", "Encoding categorical variables", "Scaling/normalizing numeric features", "Deleting the entire dataset"],
          ["Handling missing values", "Encoding categorical variables", "Scaling/normalizing numeric features"]),
        tf("q4", "A pandas DataFrame is a 2-dimensional labeled data structure, similar to a table with rows and columns.", True),
        q("q5", "single", "What is the primary purpose of data preprocessing in an AI workflow?",
          ["To make the dataset larger", "To clean and prepare raw data so a model can learn from it effectively", "To encrypt the data", "To delete unused Python packages"],
          ["To clean and prepare raw data so a model can learn from it effectively"]),
    ),
    "Machine Learning Fundamentals": five(
        q("q1", "single", "What is the key difference between supervised and unsupervised learning?",
          ["Supervised learning uses labeled data; unsupervised learning finds patterns in unlabeled data", "Supervised learning is always faster", "Unsupervised learning requires more labeled data", "There is no real difference"],
          ["Supervised learning uses labeled data; unsupervised learning finds patterns in unlabeled data"]),
        q("q2", "single", "Which algorithm is typically used to predict a continuous numeric value (e.g. house price)?",
          ["Linear Regression", "K-Means Clustering", "Logistic Regression", "PCA"],
          ["Linear Regression"]),
        q("q3", "single", "Logistic Regression is primarily used for which type of task?",
          ["Classification", "Clustering", "Dimensionality reduction", "Image compression"],
          ["Classification"]),
        tf("q4", "Overfitting means a model performs very well on training data but poorly on new, unseen data.", True),
        q("q5", "multi", "Which of these are unsupervised learning techniques covered in this module?",
          ["Clustering", "Principal Component Analysis (PCA)", "Linear Regression", "Logistic Regression"],
          ["Clustering", "Principal Component Analysis (PCA)"]),
    ),
    "Deep Learning Fundamentals": five(
        q("q1", "single", "What is the basic computational unit of a neural network called?",
          ["A neuron (or node)", "A pixel", "A tensor register", "A kernel driver"],
          ["A neuron (or node)"]),
        q("q2", "single", "What is the purpose of backpropagation in training a neural network?",
          ["To randomly initialize weights", "To compute gradients and update weights to reduce error", "To visualize the network architecture", "To compress the dataset"],
          ["To compute gradients and update weights to reduce error"]),
        q("q3", "single", "Convolutional Neural Networks (CNNs) are most commonly associated with which task?",
          ["Image-related tasks", "Tabular spreadsheet sorting", "Email delivery", "File compression"],
          ["Image-related tasks"]),
        q("q4", "single", "Recurrent Neural Networks (RNNs) are especially well-suited for which type of data?",
          ["Sequential/time-series data (e.g. text, speech)", "Single static images only", "Unordered tabular data only", "Binary files"],
          ["Sequential/time-series data (e.g. text, speech)"]),
        tf("q5", "Forward propagation is the process of passing input data through the network to produce an output/prediction.", True),
    ),
    "Natural Language Processing": five(
        q("q1", "single", "What does NLP stand for?",
          ["Natural Language Processing", "Neural Language Programming", "Network Layer Protocol", "Numeric List Processing"],
          ["Natural Language Processing"]),
        q("q2", "multi", "Which of these are common text preprocessing steps in NLP?",
          ["Tokenization", "Removing stop words", "Stemming/lemmatization", "Increasing image resolution"],
          ["Tokenization", "Removing stop words", "Stemming/lemmatization"]),
        q("q3", "single", "Sentiment Analysis is used to determine what about a piece of text?",
          ["Its emotional tone (positive/negative/neutral)", "Its file size", "Its programming language", "Its font"],
          ["Its emotional tone (positive/negative/neutral)"]),
        q("q4", "single", "BERT and GPT are both examples of which type of model architecture?",
          ["Transformers", "Decision Trees", "K-Means", "Support Vector Machines"],
          ["Transformers"]),
        tf("q5", "Text preprocessing has no effect on the performance of an NLP model.", False),
    ),
    "Computer Vision": five(
        q("q1", "single", "What is a core step in basic image processing?",
          ["Manipulating pixel values, e.g. resizing, filtering, or converting color spaces", "Sorting text alphabetically", "Sending emails", "Compressing audio files"],
          ["Manipulating pixel values, e.g. resizing, filtering, or converting color spaces"]),
        q("q2", "single", "Which network type is the standard building block for most computer vision tasks?",
          ["Convolutional Neural Network (CNN)", "Decision Tree", "K-Means Clustering", "Naive Bayes"],
          ["Convolutional Neural Network (CNN)"]),
        q("q3", "multi", "Which of these are examples of pretrained CNN architectures mentioned in this module?",
          ["VGG", "ResNet", "Pandas", "Flask"],
          ["VGG", "ResNet"]),
        q("q4", "single", "What does Object Detection do that plain image classification does not?",
          ["It locates and labels multiple objects within an image, e.g. with bounding boxes", "It only assigns one label to the whole image", "It converts images to grayscale", "It compresses the image file size"],
          ["It locates and labels multiple objects within an image, e.g. with bounding boxes"]),
        q("q5", "single", "What is the goal of Image Segmentation?",
          ["To classify every pixel of an image into a category/region", "To delete parts of an image at random", "To rename image files", "To convert images into text"],
          ["To classify every pixel of an image into a category/region"]),
    ),
    "Reinforcement Learning": five(
        q("q1", "single", "In Reinforcement Learning, what does an 'agent' do?",
          ["Takes actions in an environment to maximize cumulative reward", "Labels training data manually", "Cleans a dataset", "Compiles source code"],
          ["Takes actions in an environment to maximize cumulative reward"]),
        q("q2", "single", "What does MDP stand for in the context of Reinforcement Learning?",
          ["Markov Decision Process", "Maximum Data Pooling", "Multi-Directional Processing", "Model Deployment Pipeline"],
          ["Markov Decision Process"]),
        q("q3", "single", "Q-Learning is best described as which kind of algorithm?",
          ["A value-based reinforcement learning algorithm that learns action-value estimates", "A supervised regression algorithm", "A clustering algorithm", "A text preprocessing technique"],
          ["A value-based reinforcement learning algorithm that learns action-value estimates"]),
        q("q4", "single", "What is the main innovation of a Deep Q-Network (DQN) over classic Q-Learning?",
          ["Using a neural network to approximate the Q-value function for large/continuous state spaces", "Removing the need for any reward signal", "Using only supervised labels instead of rewards", "Ignoring the environment's state entirely"],
          ["Using a neural network to approximate the Q-value function for large/continuous state spaces"]),
        tf("q5", "In Reinforcement Learning, the agent learns purely from rewards/penalties received from its environment, not from labeled examples.", True),
    ),
    "AI Ethics & Governance": five(
        q("q1", "multi", "Which of these are concerns commonly raised in AI Ethics?",
          ["Bias in training data", "Fairness across different groups", "Accountability for AI decisions", "The color scheme of a website"],
          ["Bias in training data", "Fairness across different groups", "Accountability for AI decisions"]),
        q("q2", "single", "What does Explainable AI (XAI) aim to achieve?",
          ["Making a model's decisions understandable and interpretable to humans", "Making a model impossible to inspect", "Making a model run faster only", "Removing all data from a model"],
          ["Making a model's decisions understandable and interpretable to humans"]),
        q("q3", "multi", "Which of these are techniques used for Explainable AI, as covered in this module?",
          ["SHAP", "LIME", "K-Means", "HTTP"],
          ["SHAP", "LIME"]),
        tf("q4", "AI systems trained on biased historical data can produce biased or unfair outcomes.", True),
        q("q5", "single", "Why do regulations and guidelines for AI matter?",
          ["They help ensure AI systems are used responsibly, safely, and fairly", "They are only relevant to hardware manufacturers", "They prevent all AI research from happening", "They only apply to social media companies"],
          ["They help ensure AI systems are used responsibly, safely, and fairly"]),
    ),
    "Generative AI & Advanced Topics": five(
        q("q1", "single", "What does GAN stand for?",
          ["Generative Adversarial Network", "General Analytics Node", "Gradient Aggregation Network", "Graphical Application Node"],
          ["Generative Adversarial Network"]),
        q("q2", "single", "In a GAN, what are the two competing networks called?",
          ["Generator and Discriminator", "Encoder and Decoder Only", "Client and Server", "Teacher and Student"],
          ["Generator and Discriminator"]),
        q("q3", "single", "What is a VAE (Variational Autoencoder) primarily used for?",
          ["Generating new data samples by learning a compressed latent representation", "Sorting a list of numbers", "Formatting text documents", "Managing a database"],
          ["Generating new data samples by learning a compressed latent representation"]),
        q("q4", "single", "Why is AI at the Edge (Edge Computing) useful?",
          ["It runs AI models directly on local devices, reducing latency and reliance on the cloud", "It only works when connected to a supercomputer", "It requires no data at all", "It eliminates the need for any model training"],
          ["It runs AI models directly on local devices, reducing latency and reliance on the cloud"]),
        tf("q5", "AI in Real-Time Systems requires models that can make predictions quickly enough to meet strict timing constraints.", True),
    ),
    "Capstone Project: Tweets Sentiment Analysis": five(
        q("q1", "single", "What is the first step in the Tweets Sentiment Analysis capstone workflow?",
          ["Loading the dataset", "Deploying the final model", "Writing the Streamlit app", "Publishing the trained model to production"],
          ["Loading the dataset"]),
        q("q2", "multi", "Which of these are typical text preprocessing steps for tweet data before model training?",
          ["Removing URLs/mentions/hashtags noise", "Lowercasing text", "Tokenization", "Resizing images"],
          ["Removing URLs/mentions/hashtags noise", "Lowercasing text", "Tokenization"]),
        q("q3", "single", "Why is model selection an important step in this capstone?",
          ["Different models trade off accuracy, speed, and complexity differently for the task", "All models always perform identically", "Model selection is only needed for image tasks", "It has no impact on the final result"],
          ["Different models trade off accuracy, speed, and complexity differently for the task"]),
        q("q4", "single", "What is Streamlit used for in this capstone project?",
          ["Building a simple interactive web app to showcase the sentiment analysis model", "Training the model from scratch", "Storing the raw dataset", "Managing the MongoDB database"],
          ["Building a simple interactive web app to showcase the sentiment analysis model"]),
        tf("q5", "In this capstone, the workflow goes from raw data loading, through preprocessing and model training, to a deployable app.", True),
    ),
}


# =============================================================================
# MACHINE LEARNING — 9 modules
# =============================================================================

ML_QUIZZES = {
    "Introduction to Machine Learning": five(
        q("q1", "single", "Which best describes Machine Learning?",
          ["Systems that learn patterns from data rather than being explicitly programmed with rules", "A type of database query language", "A way to design web page layouts", "A fixed lookup table of answers"],
          ["Systems that learn patterns from data rather than being explicitly programmed with rules"]),
        q("q2", "multi", "Which of these are types of Machine Learning covered in this module?",
          ["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Web Development"],
          ["Supervised Learning", "Unsupervised Learning", "Reinforcement Learning"]),
        q("q3", "single", "Which of these is typically the FIRST step in the ML workflow?",
          ["Collecting and understanding the data", "Deploying the model to production", "Tuning hyperparameters", "Writing the final report"],
          ["Collecting and understanding the data"]),
        q("q4", "multi", "Which of these are commonly used Python libraries for Machine Learning?",
          ["scikit-learn", "Pandas", "NumPy", "Photoshop"],
          ["scikit-learn", "Pandas", "NumPy"]),
        tf("q5", "The ML workflow is typically a one-time process that never needs to be repeated once a model is built.", False),
    ),
    "Data Preprocessing": five(
        q("q1", "single", "Why is data preprocessing important before training a model?",
          ["Raw data is often messy, incomplete, or inconsistent, and needs cleaning for the model to learn well", "It is purely optional and never affects model quality", "It replaces the need for any model training", "It only matters for image data"],
          ["Raw data is often messy, incomplete, or inconsistent, and needs cleaning for the model to learn well"]),
        q("q2", "multi", "Which of these are valid strategies for handling missing data?",
          ["Removing rows/columns with missing values", "Imputing missing values (e.g. mean/median)", "Ignoring the problem and hoping the model handles it perfectly", "Using domain-specific default values"],
          ["Removing rows/columns with missing values", "Imputing missing values (e.g. mean/median)", "Using domain-specific default values"]),
        q("q3", "single", "What is the purpose of Normalization/Standardization?",
          ["To scale numeric features to a comparable range so no single feature dominates due to scale", "To convert numbers into text", "To remove all outliers automatically", "To increase the number of features"],
          ["To scale numeric features to a comparable range so no single feature dominates due to scale"]),
        q("q4", "single", "What is 'Encoding Categorical Data' used for?",
          ["Converting non-numeric category labels into a numeric form models can use", "Compressing image files", "Encrypting sensitive data", "Removing duplicate rows"],
          ["Converting non-numeric category labels into a numeric form models can use"]),
        q("q5", "single", "Why do we use a Train-Test Split?",
          ["To evaluate how well a model generalizes to data it hasn't seen before", "To make the dataset smaller for storage reasons only", "To remove the need for any evaluation metric", "To train two separate unrelated models"],
          ["To evaluate how well a model generalizes to data it hasn't seen before"]),
    ),
    "Supervised Learning": five(
        q("q1", "single", "What does a Loss Function measure?",
          ["How far a model's predictions are from the actual/true values", "The size of the dataset", "The number of features in the dataset", "The training time in seconds"],
          ["How far a model's predictions are from the actual/true values"]),
        q("q2", "single", "What is the main purpose of Regularization (L1/L2) in a model?",
          ["To reduce overfitting by penalizing overly complex models", "To increase training data size", "To speed up data loading", "To remove the need for a loss function"],
          ["To reduce overfitting by penalizing overly complex models"]),
        q("q3", "multi", "Which of these are classification algorithms covered in this module?",
          ["Logistic Regression", "Decision Trees", "Support Vector Machines (SVM)", "Linear Regression for continuous price prediction"],
          ["Logistic Regression", "Decision Trees", "Support Vector Machines (SVM)"]),
        q("q4", "single", "Which metric is specifically useful for imbalanced classification problems, beyond plain accuracy?",
          ["Precision, Recall, and F1-Score", "Only accuracy", "File size", "Training duration"],
          ["Precision, Recall, and F1-Score"]),
        tf("q5", "Random Forest is an ensemble method built from multiple Decision Trees.", True),
    ),
    "Unsupervised Learning: Clustering": five(
        q("q1", "single", "What is the goal of clustering algorithms?",
          ["To group similar data points together without using labeled outcomes", "To predict a single continuous numeric value", "To classify data using predefined labels", "To reduce the number of rows in a dataset randomly"],
          ["To group similar data points together without using labeled outcomes"]),
        q("q2", "single", "In K-Means Clustering, what does the 'K' represent?",
          ["The number of clusters to form", "The number of features in the dataset", "The learning rate", "The number of training epochs"],
          ["The number of clusters to form"]),
        q("q3", "single", "How does Hierarchical Clustering differ from K-Means?",
          ["It builds a tree (dendrogram) of nested clusters instead of a fixed number of flat clusters", "It requires labeled data, unlike K-Means", "It can only be used on images", "It doesn't use distance/similarity measures at all"],
          ["It builds a tree (dendrogram) of nested clusters instead of a fixed number of flat clusters"]),
        q("q4", "single", "What makes DBSCAN different from K-Means?",
          ["It's density-based and can find arbitrarily shaped clusters without pre-specifying the number of clusters", "It requires you to specify the number of clusters upfront, just like K-Means", "It only works on 1-dimensional data", "It ignores the density of data points entirely"],
          ["It's density-based and can find arbitrarily shaped clusters without pre-specifying the number of clusters"]),
        q("q5", "single", "What does the Silhouette Score help evaluate?",
          ["How well-separated and cohesive the resulting clusters are", "The accuracy of a classification model", "The size of the training dataset", "The speed of the clustering algorithm only"],
          ["How well-separated and cohesive the resulting clusters are"]),
    ),
    "Dimensionality Reduction": five(
        q("q1", "single", "What is the main goal of dimensionality reduction?",
          ["To reduce the number of features while preserving as much important information as possible", "To increase the number of rows in a dataset", "To convert a regression problem into classification", "To remove all numeric features"],
          ["To reduce the number of features while preserving as much important information as possible"]),
        q("q2", "single", "What does PCA (Principal Component Analysis) find?",
          ["New uncorrelated axes (components) that capture the most variance in the data", "The exact labels for each data point", "The optimal number of clusters", "A random subset of the original rows"],
          ["New uncorrelated axes (components) that capture the most variance in the data"]),
        q("q3", "single", "What does SVD (Singular Value Decomposition) do?",
          ["Decomposes a matrix into components that reveal its underlying structure, useful for dimensionality reduction", "Trains a neural network end-to-end", "Encrypts a dataset", "Splits data into train/test sets"],
          ["Decomposes a matrix into components that reveal its underlying structure, useful for dimensionality reduction"]),
        q("q4", "single", "t-SNE is primarily used for what purpose?",
          ["Visualizing high-dimensional data in 2D/3D while preserving local structure", "Making real-time predictions in production", "Cleaning missing values", "Encoding categorical variables"],
          ["Visualizing high-dimensional data in 2D/3D while preserving local structure"]),
        tf("q5", "Dimensionality reduction can help reduce overfitting and computation cost by removing redundant or less informative features.", True),
    ),
    "Ensemble Learning": five(
        q("q1", "single", "What is the core idea behind Ensemble Learning?",
          ["Combining multiple models to produce better predictive performance than any single model alone", "Using exactly one very large model", "Training a model with no data", "Skipping model evaluation entirely"],
          ["Combining multiple models to produce better predictive performance than any single model alone"]),
        q("q2", "single", "What does Bagging (e.g. in Random Forest) primarily aim to reduce?",
          ["Variance, by training multiple models on random subsets of data and averaging results", "The size of the dataset", "The number of features only", "The need for any evaluation metric"],
          ["Variance, by training multiple models on random subsets of data and averaging results"]),
        q("q3", "multi", "Which of these are boosting algorithms mentioned in this module?",
          ["AdaBoost", "Gradient Boosting", "XGBoost", "K-Means"],
          ["AdaBoost", "Gradient Boosting", "XGBoost"]),
        q("q4", "single", "How does Boosting fundamentally differ from Bagging?",
          ["Boosting trains models sequentially, each correcting the errors of the previous one", "Boosting trains all models completely independently and in parallel, exactly like Bagging", "Boosting only works on unsupervised problems", "Boosting requires no training data"],
          ["Boosting trains models sequentially, each correcting the errors of the previous one"]),
        q("q5", "single", "What is Stacking in ensemble learning?",
          ["Combining predictions from multiple different models using another model (a meta-learner)", "Randomly deleting weak models from an ensemble", "A synonym for Bagging with no differences", "A method that only works with one single base model"],
          ["Combining predictions from multiple different models using another model (a meta-learner)"]),
    ),
    "Advanced Topics": five(
        q("q1", "single", "What problem does SMOTE address?",
          ["Class imbalance, by generating synthetic samples for the minority class", "Missing values in numeric columns", "Overfitting in linear regression only", "Slow training speed on GPUs"],
          ["Class imbalance, by generating synthetic samples for the minority class"]),
        q("q2", "single", "What makes time series data distinct from standard tabular data?",
          ["Observations are ordered in time and often depend on previous values", "It never contains numeric values", "It cannot be visualized", "It has no real-world applications"],
          ["Observations are ordered in time and often depend on previous values"]),
        q("q3", "single", "What do ARIMA and SARIMA models forecast?",
          ["Future values in a time series based on its own past values and patterns", "Image classifications", "Text sentiment", "Cluster assignments"],
          ["Future values in a time series based on its own past values and patterns"]),
        q("q4", "single", "What is the goal of a Recommendation System?",
          ["To suggest relevant items to users based on their preferences or behavior", "To classify emails as spam or not spam", "To detect objects in an image", "To reduce the number of features in a dataset"],
          ["To suggest relevant items to users based on their preferences or behavior"]),
        q("q5", "multi", "Which of these are common ways to save/load a trained ML model in Python?",
          ["joblib", "pickle", "Deleting the model object", "Printing the model to the console"],
          ["joblib", "pickle"]),
    ),
    "Explainability and Ethics": five(
        q("q1", "single", "What do SHAP and LIME both help with?",
          ["Explaining individual predictions of a machine learning model", "Speeding up model training", "Cleaning missing data", "Splitting data into train/test sets"],
          ["Explaining individual predictions of a machine learning model"]),
        q("q2", "single", "Why is model explainability important in real-world ML systems?",
          ["It builds trust and helps diagnose bias or errors in model decisions", "It has no practical value once a model performs well", "It is required only for image models", "It replaces the need for model evaluation metrics"],
          ["It builds trust and helps diagnose bias or errors in model decisions"]),
        q("q3", "multi", "Which of these are Ethical AI / ML concerns covered in this module?",
          ["Bias", "Privacy", "Fairness", "Font size of a report"],
          ["Bias", "Privacy", "Fairness"]),
        q("q4", "single", "What does GDPR relate to, in the context of ML ethics?",
          ["Data privacy and protection regulations", "A machine learning algorithm", "A type of neural network layer", "A Python library for plotting"],
          ["Data privacy and protection regulations"]),
        tf("q5", "A highly accurate model can still be unethical to deploy if it is significantly biased against a group of people.", True),
    ),
    "Capstone Project: Customer Churn Prediction": five(
        q("q1", "single", "What is 'customer churn' in this capstone project?",
          ["Customers stopping their use of a company's product or service", "A type of data preprocessing technique", "A clustering algorithm", "A file format for storing models"],
          ["Customers stopping their use of a company's product or service"]),
        q("q2", "single", "Why would a business want to predict customer churn in advance?",
          ["To proactively retain at-risk customers before they leave", "To increase server response time", "To remove the need for customer support", "To automatically delete inactive customer records"],
          ["To proactively retain at-risk customers before they leave"]),
        q("q3", "single", "Customer Churn Prediction is best framed as which type of ML problem?",
          ["A classification problem (churn vs. not churn)", "A clustering problem with no labels", "A pure dimensionality reduction problem", "An image segmentation problem"],
          ["A classification problem (churn vs. not churn)"]),
        q("q4", "multi", "Which steps from this course would typically apply when building this capstone?",
          ["Data preprocessing", "Model training and evaluation", "Feature engineering", "Ignoring the dataset entirely"],
          ["Data preprocessing", "Model training and evaluation", "Feature engineering"]),
        tf("q5", "Evaluating a churn prediction model only with accuracy is usually sufficient, even on an imbalanced dataset.", False),
    ),
}


def upsert_quiz(module_id, questions):
    doc = {"module_id": str(module_id), "questions": questions}
    existing = db.quizzes.find_one({"module_id": str(module_id)})
    if existing:
        db.quizzes.update_one({"_id": existing["_id"]}, {"$set": doc})
    else:
        db.quizzes.insert_one(doc)


def seed_course(course_title, quizzes_by_module_title):
    course = db.courses.find_one({"title": course_title})
    if not course:
        print(f"SKIPPED: course '{course_title}' not found — run its seed script first.")
        return
    course_id = course["_id"]
    modules = list(db.modules.find({"course_id": str(course_id)}))
    module_by_title = {m["title"]: m for m in modules}

    print(f"\n{course_title} ({course_id}) — {len(modules)} modules found")
    for module_title, questions in quizzes_by_module_title.items():
        module = module_by_title.get(module_title)
        if not module:
            print(f"  SKIPPED (module not found): {module_title}")
            continue
        upsert_quiz(module["_id"], questions)
        print(f"  Quiz ready: {module_title} ({len(questions)} questions)")


def main():
    seed_course("Artificial Intelligence", AI_QUIZZES)
    seed_course("Machine Learning", ML_QUIZZES)
    print("\nDone! Reload the LMS — each module's course player now shows a 📝 Module Quiz entry.")


if __name__ == "__main__":
    main()
