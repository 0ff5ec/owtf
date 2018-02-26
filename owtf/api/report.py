"""
owtf.api.handlers.report
~~~~~~~~~~~~~~~~~~~~~

"""

import collections
import logging
from collections import defaultdict
from time import gmtime, strftime

from flask import request
from werkzeug.exceptions import BadRequest

from owtf.api.base import APIView
from owtf.constants import RANKS
from owtf.lib import exceptions
from owtf.managers.mapping import get_mappings
from owtf.managers.plugin import get_all_test_groups
from owtf.managers.poutput import get_all_poutputs
from owtf.managers.target import get_target_config_by_id


class ReportExport(APIView):
    """
    Class handling API methods related to export report funtionality.
    This API returns all information about a target scan present in OWTF.
    :raise InvalidTargetReference: If target doesn't exists.
    :raise InvalidParameterType: If some unknown parameter in `filter_data`.
    """
    # TODO: Add API documentation.

    methods = ['GET']

    def get(self, target_id=None):
        """
        REST API - /api/targets/<target_id>/export/ returns JSON(data) for template.
        """
        if not target_id:
            raise BadRequest()
        try:
            filter_data = request.view_args
            plugin_outputs = get_all_poutputs(filter_data, target_id=target_id, inc_output=True)
        except exceptions.InvalidTargetReference as e:
            logging.warn(e.parameter)
            raise BadRequest()
        except exceptions.InvalidParameterType as e:
            logging.warn(e.parameter)
            raise BadRequest()
        # Group the plugin outputs to make it easier in template
        grouped_plugin_outputs = defaultdict(list)
        for output in plugin_outputs:
            output['rank'] = RANKS.get(max(output['user_rank'], output['owtf_rank']))
            grouped_plugin_outputs[output['plugin_code']].append(output)

        # Needed ordered list for ease in templates
        grouped_plugin_outputs = collections.OrderedDict(sorted(grouped_plugin_outputs.items()))

        # Get mappings
        mappings = request.view_args.get("mapping", None)
        if mappings:
            mappings = get_mappings(mappings)

        # Get test groups as well, for names and info links
        test_groups = {}
        for test_group in get_all_test_groups():
            test_group["mapped_code"] = test_group["code"]
            test_group["mapped_descrip"] = test_group["descrip"]
            if mappings and test_group['code'] in mappings:
                code, description = mappings[test_group['code']]
                test_group["mapped_code"] = code
                test_group["mapped_descrip"] = description
            test_groups[test_group['code']] = test_group

        vulnerabilities = []
        for key, value in list(grouped_plugin_outputs.items()):
            test_groups[key]["data"] = value
            vulnerabilities.append(test_groups[key])

        result = get_target_config_by_id(target_id)
        result["vulnerabilities"] = vulnerabilities
        result["time"] = strftime("%Y-%m-%d %H:%M:%S", gmtime())

        if result:
            self.respond(result)
        else:
            raise BadRequest()
