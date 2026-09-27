from sklearn.impute import SimpleImputer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline


def build_search(cv, quick: bool, random_state: int):
    from xgboost import XGBClassifier
    return RandomizedSearchCV(
        Pipeline([('imputer', SimpleImputer(strategy='median')), ('model', XGBClassifier(objective='binary:logistic', eval_metric='auc', random_state=random_state, n_jobs=-1, tree_method='hist'))]),
        {'model__n_estimators': [200, 400] if quick else [200, 400, 600, 800], 'model__learning_rate': [0.03, 0.05, 0.1], 'model__max_depth': [3, 5, 7, 9], 'model__min_child_weight': [1, 3, 5], 'model__subsample': [0.7, 0.85, 1.0], 'model__colsample_bytree': [0.7, 0.85, 1.0], 'model__gamma': [0, 0.5, 1], 'model__reg_alpha': [0, 0.1, 1], 'model__reg_lambda': [1, 3, 5]},
        n_iter=4 if quick else 20, scoring='roc_auc', cv=cv, random_state=random_state, n_jobs=-1, verbose=1,
    )
