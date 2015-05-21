#!/usr/bin/python -tt

import logging
import sys
import getopt
import time
sys.path.append("/usr/share/fence")
from fencing import SyslogLibHandler
from novaclient import client


class AsyncEvacuate():

    def __init__(self, hostname, user, password, tenant, auth_url, attempt_num=60):
        """
        :param hostname: name of host from which we will evacuate
        :param attempt_num: how many times try to evacuate VMs
        :return: None
        """

        self._hostname = str(hostname)
        self._attempt_num = attempt_num
        self._nova = client.Client(2, user, password, tenant, auth_url)

    def host_evacuate(self, on_shared_storage):
        """
        This tries to evacuate instances from host
        as long as host is down
        :param on_shared_storage: tells if shared storage is used
        :return: None
        """
        nova = self._nova
        attempts = 0

        self._wait_for_host_state("down")

        while attempts < self._attempt_num:
            try:
                host = nova.hypervisors.search(self._hostname)[0]
                servers = self.get_active_instances()
                if servers and host.state is not 'up':
                    for server in servers:
                        server.evacuate(on_shared_storage=on_shared_storage)
                    break
                elif host.state is 'up':
                    break
            except Exception as e:
                time.sleep(1)
                logging.debug("Cannot evacuate due to: %s" % str(e))
            finally:
                attempts += 1

        if attempts == self._attempt_num:
            logging.info("Cannot evacuate VMs after %s attempts" % str(self._attempt_num))
        else:
            logging.info("VMs successfully evacuated")

    def get_active_instances(self):
        """
        Return list of active instances running on host
        :return: List of active instances running on host
        :rtype: list
        """
        return self._nova.servers.list(search_opts={
            'host': self._hostname,
            'status': 'ACTIVE'})

    def _wait_for_host_state(self, state):
        """
        Waits till host is in given state
        :param state: wanted state of host
        :return: None
        """
        logging.debug("Wait for host to have state: %s" % state)
        nova = self._nova
        end = False
        # some kind of timeout shall be added?
        while not end:
            try:
                logging.debug('Waiting for nova to update it internal state')
                services = nova.services.list(self._hostname)
                for service in services:
                    if service.binary == "nova-compute" and service.state == state:
                        end = True
                        break
                time.sleep(1)
            except Exception as e:
                logging.debug("Exception %s" % str(e))
                time.sleep(1)


def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger().addHandler(SyslogLibHandler())
    param_dict = {
        "--user": None,
        "--pass": None,
        "--tenant": None,
        "--name": None,
        "--auth_url": None,
        "--on_shared_storage": None
    }

    try:
        opts, args = getopt.getopt(argv, "",
                                   ["user=",
                                   "pass=",
                                   "tenant=",
                                   "name=",
                                   "auth_url=",
                                   "on_shared_storage="])
    except getopt.GetoptError:
        logging.info("Wrong parameter passed into script")
        sys.exit(2)

    for opt, arg in opts:
        param_dict[opt] = arg

    for key, value in param_dict.items():
        if value is None:
            logging.info("value of %s is not set" % key)
            sys.exit(1)

    ae = AsyncEvacuate(param_dict["--name"],
                       param_dict["--user"],
                       param_dict["--pass"],
                       param_dict["--tenant"],
                       param_dict["--auth_url"])
    ae.host_evacuate(False if param_dict["--on_shared_storage"] == "False" else True)

if __name__ == "__main__":
    main(sys.argv[1:])
