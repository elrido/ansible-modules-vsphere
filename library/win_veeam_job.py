#!/usr/bin/python
# -*- coding: utf-8 -*-

# Create or disable a VMware Veeam backup job
#
# This module creates or disables a VMware Veeam backup job and changes its
# settings. There is currently no Powershell commandlet to remove jobs, so
# setting the state to absent disables the schedule of an already existing job.
#
# (c) 2016, Simon Rupf <simon@rupf.net>
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: win_veeam_job
short_description: Create or disable a VMware Veeam backup job
description:
    - This module creates or disables a VMware Veeam backup job and changes its settings. There is currently no Powershell commandlet to remove jobs, so setting the state to absent disables the schedule of an already existing job.
version_added: "not yet"
notes:
    - This module must be executed on the Veeam server
    - This module supports VMware vSphere backups, Microsoft Hyper-V currently isn't supported
    - Tested on VMware Veeam 9.0 and VMware vSphere 5.5
requirements:
    - "pywinrm>=0.1.1"
options:
  name:
    description:
      - Name of the backup job to create, change or disable on the Veeam server.
    required: true
  state:
    description:
      - State of the backup job on the Veeam server.
    required: false
    choices:
      - present
      - absent
    default: present
  hosts:
    description:
      - Name of a single host or a comma-separated list of hosts. These are the guest VM names as used in your vCenter. May use wildcards.
    required: true
  repository:
    description:
      - Name of a single backup repository or a comma-separated list of backup repositories.
    required: true
  repository_scaleout:
    description:
      - Enables or disables the search for scale out repositories.
    required: false
    choices:
      - yes
      - no
    default: no
  algorithm:
    description:
      - In Incremental mode the first job run creates a full backup file, and the subsequent runs backups only store the changed blocks. In ReverseIncremental mode every job run creates a full backup file by merging a previous full backup with recent changes.
    required: false
    choices:
      - Incremental
      - ReverseIncremental
    default: Incremental
  filesystem_indexing:
    description:
      - Enables or disables guest file system indexing.
    required: false
    choices:
      - yes
      - no
    default: no
  retain_days:
    description:
      - Specifies the number of days to keep backup data for deleted VMs. If ommited, the data retention period will be set to 14 days by default.
    required: false
    default: 14
  schedule:
    description:
      - Specifies the schedule type. Supported are daily and monthly backups, as well as free form periods and running after other jobs are completed.
    required: false
    choices:
      - Daily
      - Monthly
      - Periodicaly
      - After
    default: Daily
  after:
    description:
      - If running in "after" schedule, this parameter specifies the job name after which the current job should be run.
    required: false
  hour:
    description:
      - For daily and monthly schedules, this specifies the hour of the day (0-23) at which the job should be started. If not set, the job will start at 10 by default.
    required: false
    default: 10
  day:
    description:
      - For daily and monthly schedules, this specifies the day of week to run the job.
    required: false
    choices:
      - Sunday
      - Monday
      - Tuesday
      - Wednesday
      - Thursday
      - Friday
      - Saturday
  day_in_month:
    description:
      - For monthly schedules, this specifies the period condition for the job run. Use this parameter to set the condition for the days parameter, i.e. to run the job on first Saturday every month.
    required: false
    choices:
      - First
      - Second
      - Third
      - Forth
      - Last
      - OnDay
  month:
    description:
      - For monthly schedules, this specifies the month to run the job.
    required: false
    choices:
      - January
      - February
      - March
      - April
      - May
      - June
      - July
      - August
      - September
      - October
      - November
      - December
  period:
    description:
      - For periodic schedules, this sets the time period to run the job as integer, i.e. set the period to 4 when running every 4 hours.
    required: false
  period_type:
    description:
      - For periodic schedules, this specifies the measurement unit for the time period. When set to Continuously, the job will run continuously starting right after it has finished and no period value is required.
    required: false
    choices:
      - Hours
      - Minutes
      - Continuously
  full:
    description:
      - Enables or disables the scheduling of active full backups.
    required: false
    choices:
      - yes
      - no
    default: no
  full_type:
    description:
      - Sets the daily or monthly period to schedule the full backup.
    required: false
    choices:
      - Daily
      - Monthly
  full_day:
    description:
      - Specifies the day to perform the full backup at.
    required: false
    choices:
      - Sunday
      - Monday
      - Tuesday
      - Wednesday
      - Thursday
      - Friday
      - Saturday
  full_day_in_month:
    description:
      - Specifies the period condition for the monthly full backup job run. Use this parameter to set the condition for the full_day parameter, i.e. to run the full backup on first Saturday every month.
    required: false
    choices:
      - First
      - Second
      - Third
      - Forth
      - Last
  full_month:
    description:
      - Specifies the month to run the full backup.
    required: false
    choices:
      - January
      - February
      - March
      - April
      - May
      - June
      - July
      - August
      - September
      - October
      - November
      - December
  transform_full_to_syntethic:
    description:
      - Used with incremental backup algorithm. If enabled a full synthetic backup will be created when the automatic first full backup falls out of retention. Otherwise, you will have to perform full backups manually or using a full backup schedule (see parameters starting with full).
    required: false
    choices:
      - yes
      - no
    default: no
  transform_increments_to_syntethic:
    description:
      - Used with incremental backup algorithm. If enabled the previous full backup chain will be transformed into a reversed incremental backup chain. Otherwise all created synthetic fulls will remain on disk. Used to save disk space.
    required: false
    choices:
      - yes
      - no
    default: no
  transform_to_syntethic_days:
    description:
      - Specifies the day to perform synthetic fulls.
    required: false
    choices:
      - Sunday
      - Monday
      - Tuesday
      - Wednesday
      - Thursday
      - Friday
      - Saturday
  vss:
    description:
      - Enable or disable VSS (Volume Shadow Services), a Windows OS service allowing to copy files of running applications that can be modified at the moment of copying. The VSS-aware applications typically are Active Directory, Microsoft SQL, Microsoft Exchange, Sharepoint, etc. To create a transactionally consistent backup of a VM running VSS-aware applications without shutting them down, Veeam uses application-aware image processing. It allows to backup the data fully and consistently. Requires to also set the user parameter.
    required: false
    choices:
      - yes
      - no
    default: no
  user:
    description:
      - Specifies the credentials to use when the vss parameter is enabled. Valid credentials need to already have been configured in Veeam.
    required: false
author:
    - Simon Rupf
'''
EXAMPLES = '''
# minimal example to create a backup job
- win_veeam_job:
    name: Minimal backup job
    hosts: MyVM01
    repository: MyTapeRepo
# example creating a daily incremental backup job, including monthly full backups
- win_veeam_job:
    name: Nightly backup job
    hosts: MyVM*
    repository: MyTapeRepo
    filesystem_indexing: yes
    retain_days: 90
    hour: 2
    full: yes
    full_type: Monthly
    full_day: Saturday
    full_day_in_month: First
    vss: yes
    user: Administrator
'''
