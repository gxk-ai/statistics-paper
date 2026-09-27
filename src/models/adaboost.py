from sklearn.ensemble import AdaBoostClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier


def build_search(cv, quick: bool, random_state: int) -> RandomizedSearchCV:
    return RandomizedSearchCV(
        Pipeline([('imputer', SimpleImputer(strategy='median')), ('model', AdaBoostClassifier(estimator=DecisionTreeClassifier(random_state=random_state), random_state=random_state))]),
        {'model__n_estimators': [100, 200] if quick else [100, 200, 400, 600], 'model__learning_rate': [0.05, 0.1, 0.3, 0.5, 1.0], 'model__estimator__max_depth': [1, 2, 3], 'model__estimator__min_samples_leaf': [1, 2, 5], 'model__estimator__class_weight': [None, 'balanced']},
        n_iter=4 if quick else 20, scoring='roc_auc', cv=cv, random_state=random_state, n_jobs=-1, verbose=1,
    )
