def get_model_attributes(instance):
    return {key: value for key, value in instance.__dict__.items() if not key.startswith("_")}
