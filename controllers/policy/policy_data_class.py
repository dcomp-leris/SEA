import uuid


class policy:
    p_data = dict()

    def __init__(self, p, db_credentials, slice_id, sp_id=None):
        self.p_data["slice_id"] = slice_id
        self.p_data["sp_id"] = sp_id
        self.p_data["p_name"] = p["name"]
        self.p_data["elasticity-type"] = p["elasticity-type"]
        self.p_data["algorithm"] = p["algorithm"]
        self.p_data["action"] = p["elasticity-action"]
        self.p_data["db_credentials"] = db_credentials
        self.p_data["p_id"] = str(uuid.uuid4())
        self.p_data["status"] = "unlocked"





