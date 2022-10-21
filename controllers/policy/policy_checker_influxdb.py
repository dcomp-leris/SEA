from influxdb_client import InfluxDBClient
from influxdb_client.domain.lesser_threshold import LesserThreshold
from influxdb_client.domain.greater_threshold import GreaterThreshold
from influxdb_client.domain.check_status_level import CheckStatusLevel
from influxdb_client.domain.threshold_check import ThresholdCheck
from influxdb_client.domain.dashboard_query import DashboardQuery
from influxdb_client.domain.query_edit_mode import QueryEditMode
from influxdb_client.domain.rule_status_level import RuleStatusLevel
from influxdb_client.domain.status_rule import StatusRule
from influxdb_client.domain.task_status_type import TaskStatusType
from influxdb_client.domain.http_notification_endpoint import HTTPNotificationEndpoint
from influxdb_client.domain.http_notification_rule import HTTPNotificationRule
from influxdb_client.service.checks_service import ChecksService
from influxdb_client.service.notification_endpoints_service import NotificationEndpointsService
from influxdb_client.service.notification_rules_service import NotificationRulesService
from influxdb_client.service.organizations_service import OrganizationsService
import datetime


class policyCheckerInfluxDB:
    # Credentials

    @staticmethod
    def create_checker(pol):
        print("POLICY:", pol.p_data)
        pol = pol.p_data
        sp_id = pol["sp_id"]
        url = pol["db_credentials"]["url"]
        token = pol["db_credentials"]["token"]
        org_name = pol["db_credentials"]["org-name"]
        bucket_name = pol["db_credentials"]["bucket-name"]
        elasticity_url = pol["db_credentials"]["elasticity-url"]
        action = pol["action"]
        print("ACTION:", action)
        uniqueId = str(datetime.datetime.now())

        with InfluxDBClient(url=url, token=token, org=org_name, debug=False) as client:
            org = client.organizations_api().find_organizations(org=org_name)[0]
            print(org.id)
            if pol["algorithm"]["type"] == "threshold":
                algorithm_trigger = pol["algorithm"]["algorithm-parameters"]["triggers"]
                threshold = None
                if algorithm_trigger[0]["operator"] in [">", ">="]:
                    threshold = GreaterThreshold(value=algorithm_trigger[0]["threshold"],
                                                 level=CheckStatusLevel.CRIT)
                else:
                    threshold = LesserThreshold(value=algorithm_trigger[0]["threshold"],
                                                level=CheckStatusLevel.CRIT)
                metric_name = algorithm_trigger[0]["metric-name"]
                query = ""
                print("ANDRER %s" % algorithm_trigger[0]["function"])
                if algorithm_trigger[0]["function"] == "mean":
                    query = f'''
                            from(bucket:"{bucket_name}")
                                |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                                |> filter(fn: (r) => r["_measurement"] == "{metric_name}")
                                |> filter(fn: (r) => r["_field"] == "value")
                                |> filter(fn: (r) => r["slice_part_id"] == "{sp_id[0]}")
                                |> aggregateWindow(every: 1s, fn:mean, createEmpty: false)
                                |> yield(name: "mean")
                            '''
                elif algorithm_trigger[0]["function"] == "derivative":
                    query = f'''
                            from(bucket:"{bucket_name}")
                                |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
                                |> filter(fn: (r) => r["_measurement"] == "{metric_name}")
                                |> filter(fn: (r) => r["_field"] == "value")
                                |> filter(fn: (r) => r["slice_part_id"] == "{sp_id[0]}")
                                |> derivative(unit: 1s, nonNegative: false)
                                |> yield(name: "derivative")
                            '''

                every = str(algorithm_trigger[0]["statistic"]["threshold-seconds"])
                print("ANDRER QUERY %s" % query)
                p_id = pol["p_id"]
                check = ThresholdCheck(name=f"Check created by Remote API_{uniqueId}",
                                       status_message_template=f"{pol['p_id']}",
                                       every=every,
                                       offset="0s",
                                       tags=[{"key": "pol_id", "value": p_id}],
                                       query=DashboardQuery(edit_mode=QueryEditMode.ADVANCED, text=query),
                                       thresholds=[threshold],
                                       org_id=org.id,
                                       status=TaskStatusType.ACTIVE
                                       )
                checks_service = ChecksService(api_client=client.api_client)
                checks_service.create_check(check)

                elasticity_url = elasticity_url + "/" + pol["elasticity-type"]
                notification_endpoint = HTTPNotificationEndpoint(name=f"Slice Elasticity_{uniqueId}",
                                                                 url=elasticity_url,
                                                                 org_id=org.id,
                                                                 method="POST",
                                                                 auth_method="none")

                notification_endpoint_service = NotificationEndpointsService(api_client=client.api_client)
                notification_endpoint = notification_endpoint_service.create_notification_endpoint(
                    notification_endpoint)

                notification_rule = HTTPNotificationRule(name=f"Critical status to Endpoint_{uniqueId}",
                                                         every=algorithm_trigger[0]["statistic"]["threshold-seconds"],
                                                         offset="0s",
                                                         description="${ r._message } Policy ID: " + pol["p_id"],
                                                         status_rules=[StatusRule(current_level=RuleStatusLevel.CRIT)],
                                                         tag_rules=[{"key": "pol_id", "value": p_id}],
                                                         endpoint_id=notification_endpoint.id,
                                                         org_id=org.id,
                                                         status=TaskStatusType.ACTIVE)

                notification_rules_service = NotificationRulesService(api_client=client.api_client)
                notification_rules_service.create_notification_rule(notification_rule)
                # Testing the creations
                """
                    List all Checks
                """
                print(f"\n------- Checks: -------\n")
                checks = checks_service.get_checks(org_id=org.id).checks
                print("\n".join([f" ---\n ID: {it.id}\n Name: {it.name}\n Type: {type(it)}" for it in checks]))
                print("---")

                """
                List all Endpoints
                """
                print(f"\n------- Notification Endpoints: -------\n")
                notification_endpoints = notification_endpoint_service.get_notification_endpoints(
                    org_id=org.id).notification_endpoints
                print("\n".join(
                     [f" ---\n ID: {it.id}\n Name: {it.name}\n Type: {type(it)}" for it in notification_endpoints]))
                print("---")

                """
                List all Notification Rules
                """
                print(f"\n------- Notification Rules: -------\n")
                notification_rules = notification_rules_service.get_notification_rules(org_id=org.id).notification_rules
                print("\n".join(
                    [f" ---\n ID: {it.id}\n Name: {it.name}\n Type: {type(it)}" for it in notification_rules]))
                print(f"--- {datetime.datetime.now()}")

        return 200
