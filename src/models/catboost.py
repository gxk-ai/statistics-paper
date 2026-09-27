from sklearn.model_selection import RandomizedSearchCV


def build_search(cv, quick: bool, random_state: int, balanced: bool = False):
    from catboost import CatBoostClassifier
    return RandomizedSearchCV(
        CatBoostClassifier(loss_function='Logloss', eval_metric='AUC', random_seed=random_state, verbose=False, allow_writing_files=False, auto_class_weights='Balanced' if balanced else None),
        {'iterations': [50, 100] if quick else [300, 500, 800, 1200], 'depth': [4, 6, 8, 10], 'learning_rate': [0.03, 0.05, 0.1], 'l2_leaf_reg': [1, 3, 5, 10], 'random_strength': [0.5, 1, 2], 'bagging_temperature': [0, 0.5, 1], 'border_count': [64, 128]},
        n_iter=3 if quick else 12, scoring='roc_auc', cv=cv, random_state=random_state, n_jobs=1, verbose=1,
    )
