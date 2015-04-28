#!/usr/bin/python -tt

import subprocess
import threading
import logging
import shlex
import sys


class AsyncEvacuate():

    def __init__(self, hostname, command, timeout=5):
        """
        :param hostname: name of host from which we will evacuate
        :param command: command to perform
        :return: None
        """

        logging.basicConfig(filename='/tmp/async_evacuate.log', level=logging.DEBUG)
        self._hostname = str(hostname)
        self._command = command
        self._timeout = timeout

    def run(self):
        """
        This disables host in pacemaker
        then evacuate all the vm's
        at last it enables host again
        :return: None
        """

        try:
            self._disable_host()
            self._run_command()
        except Exception as err:
            logging.error("Evacuating failed due to error")
            logging.debug(str(err))
        finally:
            self._enable_host()

    @staticmethod
    def run_process(command, timeout):
        """
        Runs process for given amount of time, then kills it
        :return: process.wait() if process exited normally, 1 if it was killed
        :rtype int
        """
        process = subprocess.Popen(shlex.split(command))

        thread = threading.Thread(target=process.wait)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            process.kill()
            return 1

        return process.wait()

    def _disable_host(self):
        """
        Disables host in pacemaker
        :return: None
        """

        command = "pcs resource disable %s" % self._hostname
        logging.info("Disabling host %s in pacemaker" % self._hostname)

        # if run_process returns 1, it was killed - therefore Exception is raised
        if AsyncEvacuate.run_process(command, self._timeout):
            msg = "Cannot disable host in pacemaker"
            raise Exception(msg)

        logging.info("Host %s disabled in pacemaker" % self._hostname)

    def _run_command(self):
        """
        Evacuates all VMs from given host
        :return: None
        """

        logging.info("Evacuating vms from host %s" % self._hostname)

        process = subprocess.Popen(shlex.split(self._command))
        # theoretically call to nova always ends
        # but maybe some big timeout shall be added?
        process.wait()

        logging.info("Evacuating vms from host %s ended" % self._hostname)

    def _enable_host(self):
        """
        Enables host in pacemaker
        :return: None
        """

        command = "pcs resource enable %s" % self._hostname
        logging.info("Enabling host %s in pacemaker" % self._hostname)

        # if run_process returns 1, it was killed - therefore Exception is raised
        if AsyncEvacuate.run_process(command, self._timeout):
            msg = "Cannot enable host in pacemaker"
            raise Exception(msg)

        logging.info("Host %s enabled in pacemaker" % self._hostname)


def main():
    if len(sys.argv) != 3:
        sys.exit(1)

    hostname, command = sys.argv[1:]
    ae = AsyncEvacuate(hostname, command)
    ae.run()

if __name__ == "__main__":
    main()