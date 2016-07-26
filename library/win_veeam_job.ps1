#!powershell
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
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# WANT_JSON
# POWERSHELL_COMMON

# adapted from Ansibles Get-AnsibleParam, used for integer validation
#Example: Get-Int -obj $params -name "Minutes" -default 30 -resultobj $result -failifempty $true -min 0 -max 59
Function Get-Int($obj, $name, $default = $null, $resultobj, $failifempty=$false, $emptyattributefailmessage, [int]$min=0, [int]$max=[int]::MaxValue) {
    try {
        if (-not $obj.$name.GetType) {
            throw
        }

        if ($obj.$name -is [int] -and $obj.$name -ge $min -and $obj.$name -le $max) {
            $obj.$name
        } else {
            Fail-Json -obj $resultobj -message "Argument $name needs to be an integer between $min and $max but was $($obj.$name)."
        }
    } catch {
        if ($failifempty -eq $false) {
            $default
        } else {
            if (!$emptyattributefailmessage) {
                $emptyattributefailmessage = "Missing required argument: $name"
            }
            Fail-Json -obj $resultobj -message $emptyattributefailmessage
        }
    }
}

# variables
$result = New-Object PSObject -Property @{
    changed = $false
    changes = @()
    success = $false
}
$states             = @("present","absent")
$days               = @("Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday")
$days_in_month      = @("First","Second","Third","Forth","Last","OnDay")
$full_days_in_month = @("First","Second","Third","Forth","Last")
$months             = @("January","February","March","April","May","June","July","August","September","October","November","December")
$algorithms         = @("ReverseIncremental","Incremental")
$schedules          = @("Daily","Monthly","Periodicaly","After")
$periods            = @("Hours","Minutes","Continuously")
$types              = @("Daily","Monthly")



# parameter validation, defaults are based on the Veeam Powershell documentation
$params = Parse-Args $args $true;
$check_mode                        = Get-Attr $params "_ansible_check_mode" $false | ConvertTo-Bool
$name                              = Get-Attr $params "name" -FailIfEmpty $true
$state                             = Get-Attr $params "state" "present"             -ResultObj $result -ValidateSet $states
$hosts                             = Get-Attr $params "hosts" -FailIfEmpty $true | % { $_.Split(',').Trim() }
$repository                        = Get-Attr $params "repository" -FailIfEmpty $true
$repository_scaleout               = Get-Attr $params "repository_scaleout" $false | ConvertTo-Bool
$algorithm                         = Get-Attr $params "algorithm" "Incremental"     -ResultObj $result -ValidateSet $algorithms
$filesystem_indexing               = Get-Attr $params "filesystem_indexing" $false | ConvertTo-Bool
$retain_days                       = Get-Int  $params "retain_days" 14              -ResultObj $result -Min 1
$schedule                          = Get-Attr $params "schedule" "Daily"            -ResultObj $result -ValidateSet $schedules
$after                             = Get-Attr $params "after"
$hour                              = Get-Int  $params "hour" 10                     -ResultObj $result -Max 23
$day                               = Get-Attr $params "day"                         -ResultObj $result -ValidateSet $days
$day_in_month                      = Get-Attr $params "day_in_month"                -ResultObj $result -ValidateSet $days_in_month
$month                             = Get-Attr $params "month"                       -ResultObj $result -ValidateSet $months
$period                            = Get-Int  $params "period"                      -ResultObj $result -Min 1
$period_type                       = Get-Attr $params "period_type"                 -ResultObj $result -ValidateSet $periods
$full                              = Get-Attr $params "full" $false | ConvertTo-Bool
$full_type                         = Get-Attr $params "full_type"                   -ResultObj $result -ValidateSet $types
$full_day                          = Get-Attr $params "full_day"                    -ResultObj $result -ValidateSet $days
$full_day_in_month                 = Get-Attr $params "full_day_in_month"           -ResultObj $result -ValidateSet $full_days_in_month
$full_month                        = Get-Attr $params "full_month"                  -ResultObj $result -ValidateSet $months
$transform_full_to_syntethic       = Get-Attr $params "transform_full_to_syntethic" $false | ConvertTo-Bool
$transform_increments_to_syntethic = Get-Attr $params "transform_increments_to_syntethic" $false | ConvertTo-Bool
$transform_to_syntethic_days       = Get-Attr $params "transform_to_syntethic_days" -ResultObj $result -ValidateSet $days
$vss                               = Get-Attr $params "vss" $false | ConvertTo-Bool
$user                              = Get-Attr $params "user"



Add-PSSnapin VeeamPSSnapin
try {
    $job = Get-VBRJob -Name $name
} catch {
    Fail-Json $result $_.Exception.Message
}

if ($state -eq "present") {
    if ($job -eq $null) {
        if (-not $check_mode) {
            try {
                $vms = Find-VBRViEntity -Name $hosts
                if ($repository_scaleout) {
                    $repo = Get-VBRBackupRepository -Name $repository -ScaleOut
                } else {
                    $repo = Get-VBRBackupRepository -Name $repository
                }
                $tmp = Add-VBRViBackupJob -Name $name -Entity $vms -BackupRepository $repo
                $job = Get-VBRJob -Name $name
            } catch {
                Fail-Json $result $_.Exception.Message
            }

        }
        $result.changes += "Added new backup job '$name'"
    }

    if ($vss -and $user -ne $null) {
        try {
            $credentials = Get-VBRCredentials -Name $user
            $vss_options = New-VBRJobVssOptions -ForJob
            $vss_options.Enabled = $true
            $vss_options.VssSnapshotOptions.IsCopyOnly = $true
        } catch {
            Fail-Json $result $_.Exception.Message
        }
    }

    $job_options = New-VBRJobOptions -ForBackupJob
    $job_options.BackupStorageOptions.RetainCycles = $retain_days
    $job_options.BackupStorageOptions.RetainDays = $retain_days

    $schedule_params = @{
        Job = $name
    }
    $schedule_params.Add($schedule, $true)
    if ($schedule -eq "Daily" -or $schedule -eq "Monthly") {
        $schedule_params.Add("At", "$($hour):00")
        if ($day -ne $null) {
            $schedule_params.Add("Days", $day)
        }
    }
    if ($schedule -eq "Daily") {
        $schedule_params.Add("DailyKind", "Everyday")
        if ($day -ne $null) {
            $schedule_params.Set_Item("DailyKind", "SelectedDays")
        }
    } elseif ($schedule -eq "Monthly") {
        if ($day -ne $null -and $day_in_month -ne $null) {
            $schedule_params.Add("NumberInMonth", $day_in_month)
        }
        if ($month -ne $null) {
            $schedule_params.Add("Months", $month)
        }
    } elseif ($schedule -eq "Periodicaly") {
        if ($period -ne $null) {
            $schedule_params.Add("FullPeriod", $period)
        }
        if ($period_type -ne $null) {
            $schedule_params.Add("PeriodicallyKind", $period_type)
        }
    } elseif ($schedule -eq "After") {
        if ($after -ne $null) {
            $schedule_params.Add("AfterJob", (Get-VSBJob -Name $after))
        }
    }

    $advanced_params = @{
        Job = $name
        Algorithm = $algorithm
    }
    if ($full) {
        $advanced_params.Add("EnableFullBackup", $true)
        if ($full_type -ne $null) {
            $advanced_params.Add("FullBackupScheduleKind", $full_type)
        }
        if ($full_day -ne $null) {
            $advanced_params.Add("FullBackupDays", $full_day)
        }
        if ($full_day_in_month -ne $null) {
            $advanced_params.Add("DayNumberInMonth", $full_day_in_month)
        }
        if ($full_month -ne $null) {
            $advanced_params.Add("Months", $full_month)
        }
    }
    if ($transform_full_to_syntethic) {
        $advanced_params.Add("TransformFullToSyntethic", $true)
    } else {
        $advanced_params.Add("TransformFullToSyntethic", $false)
    }
    if ($transform_increments_to_syntethic) {
        $advanced_params.Add("TransformIncrementsToSyntethic", $true)
    } else {
        $advanced_params.Add("TransformIncrementsToSyntethic", $false)
    }
    if ($transform_to_syntethic_days -ne $null) {
        $advanced_params.Add("TransformToSyntethicDays", $transform_to_syntethic_days)
    }

    if (-not $check_mode) {
        try {
            $tmp = Set-VBRJobOptions -Job $job -Options $job_options
            $tmp = Set-VBRJobSchedule @schedule_params
            $tmp = Set-VBRJobAdvancedOptions -Job $name -RetainDays $retain_days
            $tmp = Set-VBRJobAdvancedBackupOptions @advanced_params
            if ($filesystem_indexing) {
                $tmp = Enable-VBRJobGuestFSIndexing -Job $name
            } else {
                $tmp = Disable-VBRJobGuestFSIndexing -Job $name
            }
            if ($vss -and $user -ne $null) {
                $tmp = Set-VBRJobVssOptions -Job $name -Options $vss_options
                $tmp = Set-VBRJobVssOptions -Job $name -Credential $credentials
            }
            $tmp = (Get-VBRJob -Name $name | Enable-VBRJobSchedule)
        } catch {
            Fail-Json $result $_.Exception.Message
        }
    }
} elseif ($state -eq "absent") {
    if ($job -ne $null) {
        if (-not $check_mode) {
            try {
                $job | Disable-VBRJobSchedule
            } catch {
                Fail-Json $result $_.Exception.Message
            }
        }
        $result.changes += "Disabled backup job '$name' (there is currently no Powershell commandlet to remove jobs)"
    }
}

$result.success = $true
if ($result.changes.Length > 0) {
    $result.changed = $true
}
Exit-Json $result

