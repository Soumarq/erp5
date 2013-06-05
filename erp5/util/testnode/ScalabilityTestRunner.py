##############################################################################
#
# Copyright (c) 2011 Nexedi SA and Contributors. All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsibility of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# guarantees and support are strongly advised to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from datetime import datetime,timedelta
import os
import subprocess
import sys
import time
import glob
import SlapOSControler
import json
import time
import shutil
import logging
import string
import random
from ProcessManager import SubprocessError, ProcessManager, CancellationError
from subprocess import CalledProcessError
from Updater import Updater
from erp5.util import taskdistribution

class ScalabilityTestRunner():
  def __init__(self, testnode):
    self.testnode =  testnode
    self.involved_nodes = [] # doesn't change during all the test
    self.worker_nodes = [] # may change between two test_suite
    self.launcher_nodes = [] # may change between two test_suite
    self.master_nodes = [] # doesn't change during all the test
    self.slave_nodes = [] # doesn't change during all the test 


  def _prepareSlapOS(self, software_path_list):
    """
    Install softwares from list on all nodes wich are involved in the scalability test
    """ 
    for computer_guid in self.computer_guid_list:
      self.slapos_controler.initializeSlapOSControler(
                                      software_path_list, 
                                      computer_guid)
                                              
  def prepareSlapOSForTestNode(self):
    """
    Install softwares used to run tests (ex : launcher software)
    """
    for computer_guid in self.launcher_nodes['computer_id']:
      self.slapos_controler._supply(
                 software_path_list=self.config.get("software_list"),
                 computer_guid = computer_guid
              ) 

  def prepareSlapOSForTestSuite(self, software_path_list):
    """
    Install testsuite's softwares (on worker_nodes)
    """
    for computer_guid in self.worker_nodes['computer_id']:
      self.slapos_controler._supply(
                 software_path_list=software_path_list,
                 computer_guid = computer_guid
              ) 

  def _cleanUpNodesInformation(self):
    self.worker_nodes = []
    self.launcher_nodes = []

  def _generateConfigurationList(self, test_suite): 
    # TODO : implement it 
    return []

  # TODO : define methods to check if involved nodes are okay etc..
  # And if it's not end ans invalidate everything and retry/reloop




