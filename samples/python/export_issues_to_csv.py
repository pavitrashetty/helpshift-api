import requests
import csv
import sys
import datetime


DOMAIN = "<DOMAIN>"
API_KEY = "<API_KEY>"
ISSUES_FILE_LOC = "<ISSUES_FILE_LOCATION>/issues.csv"


def make_api_request(endpoint):
    response = requests.get(endpoint, auth=(API_KEY, ""))
    if response.status_code != 200:
        print "Something went wrong: " + str(response.json())
        exit(1)
    return response


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print "Please enter number of days N. Issues created in the last N days will be retrieved.\n" \
              "Usage: python export_issues_to_csv.py <NO OF DAYS>"
        exit(1)

    timestamp_in_ms = 0

    try:
        N = int(sys.argv[1])
        timestamp_in_secs = (datetime.date.today() - datetime.timedelta(days=N)).strftime("%s")
        timestamp_in_ms = long(timestamp_in_secs) * 1000
    except ValueError as ve:
        print "Wrong value given for number of days = " + sys.argv[1]
        exit(2)

    api_endpoint = "https://api.helpshift.com/v1/" + DOMAIN + "/issues?page-size=1000&created_since=" + \
                   str(timestamp_in_ms) + "&includes=%5B%22meta%22%5D&"

    with open(ISSUES_FILE_LOC, 'wb') as issues_file:

        issue_fieldnames = {'issue_id', 'user_id', 'user_email', 'title', 'assigned_to',
                            'state', 'changed_at', 'meta_order_number'}
        issue_writer = csv.DictWriter(issues_file, fieldnames=issue_fieldnames, extrasaction='ignore', restval='')
        issue_writer.writeheader()
        current_page = 0

        while True:

            current_page = current_page + 1
            api_endpoint_with_pagination = api_endpoint + 'page=' + str(current_page)

            issues_response = make_api_request(api_endpoint_with_pagination)
            resp = issues_response.json()

            if resp['total-pages'] < current_page:
                print ("Export completed. Total number of API calls: " + str(current_page - 1))
                break

            for issue in resp['issues']:
                try:

                    '''
                    NOTES:
                    1. Certain string fields that may contain non-ASCII characters have been encoded for csv writer.
                    2. We get timestamp in ms. We need to explicitly convert it to date time format.
                    3. We do not have the USER_ID (profile_id of issue author) at the top level in the GET /issues
                     response payload, but each message of issue has the id, name and email of each author.
                     We sort the messages on creation time and take id of the first message author as USER_ID.
                    '''

                    assignee_name = issue['assignee_name'].encode("utf-8") if issue['assignee_name'] else ""
                    changed_at = datetime.datetime.fromtimestamp(int(issue['state_data']['changed_at']) / 1000)

                    messages = sorted(issue['messages'], key=lambda k: k['created_at'])
                    user_id = messages[0]['author']['id']

                    issue_writer.writerow(dict(issue_id=issue['id'],
                                               user_id=user_id,
                                               user_email=issue.get('author_email', ""),
                                               assigned_to=assignee_name,
                                               title=issue.get('title', "").encode("utf-8"),
                                               state=issue['state_data']['state'],
                                               changed_at=str(changed_at),
                                               meta_order_id=issue['meta'].get('order_number', "")))
                except Exception as ee:
                    print ("Exception for Issue ID: " + str(issue['id']))
                    print (ee)
                    pass
