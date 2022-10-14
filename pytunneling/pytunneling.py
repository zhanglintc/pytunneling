#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Pytunneling

    Sets up SSH tunnel(s) that can be used to forward ports for use through firewalled environments. It
     assumes input tunnel info is accurate otherwise will fail/exit (note: in particular any SSH keys must
     exist on source server, also be sure to check SSH connectivity and no first time SSH thumbprint prompts)
"""

from sshtunnel import SSHTunnelForwarder
import logging.config
logger = logging.getLogger(__name__)


class TunnelNetwork:
    def __init__(self, tunnel_info: list, target_ip: str, target_port: int, local_host: str=None, local_port: int=None):
        """Initialise Tunnel Network
        Arguments:
            tunnel_info {list} -- List of dictionary objects containing tunnel information
                (for all fields refer to https://sshtunnel.readthedocs.io/en/latest/#sshtunnel.SSHTunnelForwarder) 
            target_ip {str} -- Address or IP for actual destination server to be forwarded
            target_port {int} -- Port number for actual destination server to be forwarded
        """
        if not tunnel_info:
            raise ValueError("No tunnels provided in input list.")

        self.tunnel_info = tunnel_info
        self.target_ip = target_ip
        self.target_port = target_port

        local_host = local_host or 'localhost'
        if local_port:
            self.local_bind = (local_host, local_port)
        else:
            self.local_bind = (local_host,)

    def __enter__(self):
        if not self.start_tunnels():
            exit(1)
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.stop_tunnels()

    def __str__(self):
        return f"TunnelNetwork(tunnel_info={self.tunnel_info}, target_ip={self.target_ip}, target_port={self.target_port})"

    def start_tunnels(self, ssh_port: int = 22):
        """Starts all tunnels
        Arguments:
            ssh_port {int} -- SSH Port (default: 22)
        Returns:
            success {bool} -- Returns true if all tunnels started successfully
        """
        self.tunnels = []
        for idx, tunnel_info in enumerate(self.tunnel_info):

            # If we're not the first element, set the bastion to the local port of the previous tunnel
            if idx > 0:
                tunnel_info['ssh_address_or_host'] = (
                    'localhost', self.tunnels[-1].local_bind_port)

            # If we are the last element, the target is the real target
            if idx == len(self.tunnel_info) - 1:
                target = (self.target_ip, self.target_port)
                tunnel_info['local_bind_address'] = self.local_bind
            # Otherwise the target is the next bastion
            else:
                target = (self.tunnel_info[idx + 1]['ssh_address_or_host'],
                          ssh_port)

            logger.debug(
                "Attempting to start tunnel to target '%s' with info '%s'",
                target, tunnel_info)
            try:
                self.tunnels.append(
                    SSHTunnelForwarder(remote_bind_address=target,
                                       **tunnel_info))
                self.tunnels[idx].start()
            except Exception as ex:
                logger.error("Unable to start tunnel to '%s', exception: %s",
                             target, ex)
                return False

        return True

    def stop_tunnels(self):
        """Stops all tunnels in reverse order"""
        for tunnel in reversed(self.tunnels):
            tunnel.stop()
        self.tunnels = []

    @property
    def tunnels_active(self):
        """Tests to see if all tunnels are active
        Returns:
            is_active {bool} -- Returns true if all tunnels active
        """
        return self.tunnels and all(
            [tunnel.is_active for tunnel in self.tunnels])

    @property
    def local_bind_port(self):
        """Gets the local bind port
        Returns:
            local_bind_port {int} -- bind port of last tunnel or None if no tunnels
        """
        if self.tunnels:
            return self.tunnels[-1].local_bind_port
        else:
            return None
