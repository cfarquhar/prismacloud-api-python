""" Categorize defenders by support lifecycle status """

import json
import re
from prismacloud.api import pc_api, pc_utility


# --Configuration-- #

parser = pc_utility.get_arg_parser()
args = parser.parse_args()

# --Initialize-- #

settings = pc_utility.get_settings(args)
pc_api.configure(settings)

# --Main-- #

# I think this list will have to be maintained manually since you can't predict future versions.
# TODO: We should probably warn users that this list needs to be updated if we see a newer version reported by an API call
MAJOR_VERSIONS = [
    "22.12",
    "22.06",
    "22.01",
    "21.08",
    "21.04",
    "20.12",
    "20.09",
    "20.04",
]


class PCCVersion:
    """
    Class to handle Prisma Cloud Compute version validation, comparisons, etc
    """

    def __init__(self, version_string=None):
        if version_string:
            if self._is_valid(version_string):
                self.version = version_string
            else:
                raise Exception(f"{version_string} is not a valid version")
        else:
            self.version = self._get_latest()

    def _is_valid(self, version_string):
        valid_regex = re.compile(r"\d{2}\.\d{2}(\.\d{3})?")
        return valid_regex.fullmatch(version_string)

    def _get_latest(self):
        resp = pc_api.settings_latest_version_read()
        version = resp.get("latestVersion", "")
        if not self._is_valid(version):
            raise Exception("Unable to extract latestVersion from API response.")
        return version

    def __eq__(self, other):
        if isinstance(other, str):
            other = PCCVersion(other)

        return bool(
            self._year == other._year
            and self._month == other._month
            and self._build == other._build
        )

    def __lt__(self, other):
        # TODO: There is probably a more succinct way to do this

        if self._year < other._year:
            return True
        if self._year > other._year:
            return False

        if self._month < other._month:
            return True
        if self._month > other._month:
            return False

        if self._build < other._build:
            return True

        return False

    def __le__(self, other):
        if self.__lt__(other) or self.__eq__(other):
            return True

        return False

    def __repr__(self):
        return self.version

    @property
    def major(self):
        return self.version[0:5]

    @property
    def _build(self):
        return self.version[6:]

    @property
    def _year(self):
        return self.version[0:2]

    @property
    def _month(self):
        return self.version[3:5]


# Get current console version
server_ver = PCCVersion()

# Get all defender versions
defenders = pc_api.defenders_list_read()


# Reverse sort known major versions
major_versions_rsorted = sorted(list(map(PCCVersion, MAJOR_VERSIONS)), reverse=True)

# Console version may not be the latest.  Discard any versions that are more recent than the console.
relevant_versions_rsorted = [
    item for item in major_versions_rsorted if item <= PCCVersion(server_ver.major)
]

n = str(relevant_versions_rsorted[0])
n1 = str(relevant_versions_rsorted[1])
n2 = str(relevant_versions_rsorted[2])

results = {"n": [], "n-1": [], "n-2": [], "unsupported": []}

# Assign defenders to support categories
for defender in defenders:
    if PCCVersion(defender["version"]).major == PCCVersion(n):
        results["n"].append(defender)
    elif PCCVersion(defender["version"]).major == PCCVersion(n1):
        results["n-1"].append(defender)
    elif PCCVersion(defender["version"]).major == PCCVersion(n2):
        results["n-2"].append(defender)
    else:
        results["unsupported"].append(defender)

print(json.dumps(results, indent=2))
