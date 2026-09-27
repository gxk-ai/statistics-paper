from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline


def build_search(cv, quick: bool, random_state: int) -> RandomizedSearchCV:
    return RandomizedSearchCV(
        Pipeline([('imputer', SimpleImputer(strategy='median')), ('model', RandomForestClassifier(random_state=random_state, n_jobs=-1))]),
        {'model__n_estimators': [300, 500] if quick else [300, 500, 800], 'model__max_depth': [None, 8, 12, 16], 'model__max_features': ['sqrt', 'log2', 0.5], 'model__min_samples_split': [2, 5, 10], 'model__min_samples_leaf': [1, 2, 5, 10], 'model__class_weight': [None, 'balanced']},
        n_iter=4 if quick else 20, scoring='roc_auc', cv=cv, random_state=random_state, n_jobs=-1, verbose=1,
    )
