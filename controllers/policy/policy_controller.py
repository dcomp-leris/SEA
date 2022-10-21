import policy
import policy_checker_influxdb


class policyInterpreter:
    def create_policies(data, db_credentials):
        policies = list()
        slice_id = data["slices"]["slice"]["slice-id"]
        slice_parts = data["slices"]["slice"]["slice-parts"]
        pol = None
        for sps in slice_parts:
            if sps.get("policies-elasticity"):
                print(sps)
                sp_id = [sps["sp-id"]]
                for p in sps["policies-elasticity"]:
                    pol = policy.policy(p, db_credentials, slice_id, sp_id)
                    if db_credentials["type"] == "influxdb":
                        pol_check = policyCheckerInfluxDB.policyCheckerInfluxDB.create_checker(pol)
                    policies.append(pol.p_data)

        if data["slices"]["slice"].get("policies-elasticity"):
            sp_id = [sp["sp-id"] for sp in slice_parts]
            print("DICT POL: ", data["slices"]["slice"]["policies-elasticity"])
            for p in data["slices"]["slice"]["policies-elasticity"]:
                pol = policy.policy(p, db_credentials, slice_id, sp_id)
                if db_credentials["type"] == "influxdb":
                    pol_check = policyCheckerInfluxDB.policyCheckerInfluxDB.create_checker(pol)
                policies.append(pol.p_data)

        return policies
