#!/usr/bin/env python

'''Build/run ubxlib for NRF52 and report results.'''

import os                    # For sep(), getcwd()
from time import time, sleep
import subprocess
import u_connection
import u_monitor
import u_report
import u_utils

# Prefix to put at the start of all prints
PROMPT = "u_run_nrf52_"

# Expected bin directory of GCC ARM compiler
GNU_INSTALL_ROOT = "C:/Program Files (x86)/GNU Tools ARM Embedded/9 2019-q4-major/bin/"

# Expected prefix for GCC ARM tools
GNU_PREFIX = "arm-none-eabi"

# Expected version of GCC ARM compiler
GNU_VERSION = "9.2.1"

# Expected path to Segger Embedded Studio command-line builder directory
SES_PATH = "C:\\Program Files\\Segger\\SEGGER Embedded Studio for ARM 4.52c\\bin"

# Expected name of Segger Embedded Studio command-line builder executable
SES_NAME = "embuild.exe"

# The build configuration to use from the Segger Embedded Studio project file
SES_BUILD_CONFIGURATION = "Debug"

# Expected location of NRF5 installation
NRF5_PATH = "C:/nrf5"

# The list of things to execute jlink.exe
RUN_JLINK = [u_utils.JLINK_PATH, "-Device", "NRF52840_XXAA", "-If", "SWD",
             "-Speed", "4000", "-Autoconnect", "1", "-ExitOnError", "1"]

# The directory where the runner build for GCC can be found
RUNNER_DIR_GCC = "port/platform/nordic/nrf52/sdk/gcc/runner"

# The directory where the runner build for SES can be found
RUNNER_DIR_SES = "port/platform/nordic/nrf52/sdk/ses/runner"

# The name of the SES project, without the .emProject extension
# so that it can also be used as the name of the binary
PROJECT_NAME_SES = "u_pca10056"

# Prefix of the build sub-directory name for GCC
BUILD_SUBDIR_PREFIX_GCC = "build_"

# The name of the output folder that the Segger Embedded Studio project uses
BUILD_SUBDIR_SES = "Output"

# The maximum number of U_FLAGx defines that the SES project file can take
SES_MAX_NUM_DEFINES = 20

# The guard time for this build in seconds,
# noting that it can be quite long when
# many builds are running in parallel.
BUILD_GUARD_TIME_SECONDS = 60 * 30

# The guard time waiting for a lock on the HW connection seconds
CONNECTION_LOCK_GUARD_TIME_SECONDS = u_connection.CONNECTION_LOCK_GUARD_TIME_SECONDS

# The guard time waiting for a platform lock in seconds
PLATFORM_LOCK_GUARD_TIME_SECONDS = u_utils.PLATFORM_LOCK_GUARD_TIME_SECONDS

# The download guard time for this build in seconds
DOWNLOAD_GUARD_TIME_SECONDS = u_utils.DOWNLOAD_GUARD_TIME_SECONDS

# The guard time for running tests in seconds
RUN_GUARD_TIME_SECONDS = u_utils.RUN_GUARD_TIME_SECONDS

# The inactivity time for running tests in seconds
RUN_INACTIVITY_TIME_SECONDS = u_utils.RUN_INACTIVITY_TIME_SECONDS

# Table of "where.exe" search paths for tools required to be installed for
# each SDK type (None = both) plus hints as to how to install the tools
# and how to read their version
TOOLS_LIST = [{"type": "gcc", "which_string": "make",
               "hint": "can't find make, please install it"                  \
                       " (e.g. from here:"                                   \
                       " http://gnuwin32.sourceforge.net/packages/make.htm)" \
                       " and ensure it is on the path.",
               "version_switch": "--version"},
              {"type": "gcc", "which_string": GNU_INSTALL_ROOT + ":" + GNU_PREFIX + "-gcc.exe",
               "hint": "can't find GCC ARM compiler expected to be found"    \
                       " in GNU_INSTALL_ROOT, please EITHER"                 \
                       " install it (no need to add it to the path)"         \
                       " or change the variable GNU_INSTALL_ROOT"            \
                       " to reflect where it is (e.g."                       \
                       " C:/Program Files (x86)/GNU Tools ARM Embedded/9 2019-q4-major/bin/)" \
                       " (and GNU_PREFIX to something like arm-none-eabi).",
               "version_switch": None},
              {"type": "ses", "which_string": SES_PATH + ":" + SES_NAME,
               "hint": "can't find the Segger Embedded Studio, command-line" \
                       " builder, expected to be found at SES_PATH,"         \
                       " please EITHER  install it (no need to add it to"    \
                       " the path) or change the variable SES_PATH"          \
                       " to reflect where it is (e.g."                       \
                       " C:\\Program Files\\Segger\\SEGGER Embedded Studio"  \
                       " for ARM 4.50\\bin\\embuild.exe).",
               "version_switch": None},
              {"type": None, "which_string": "nrfjprog.exe",
               "hint": "couldn't find the nRF5 SDK at NRF5_PATH,"            \
                       " please download the latest version from"            \
                       " https://www.nordicsemi.com/Software-and-tools/"     \
                       "Software/nRF5-SDK/Download#infotabs"                 \
                       " (no need to run an installer, no need for Soft"     \
                       " Device, just unzip the nRF5_blah zip file)"         \
                       " or override the environment variable NRF5_PATH"     \
                       " to reflect where it is.",
               "version_switch": "--version"},
              {"type": None, "which_string": u_utils.JLINK_PATH,
               "hint": "can't find the SEGGER tools, please install"         \
                       " the latest version of their JLink tools from"       \
                       " https://www.segger.com/downloads/jlink/JLink_Windows.exe" \
                       " and add them to the path.",
               "version_switch": None}]

def check_installation(sdk, tools_list, printer, prompt):
    '''Check that everything required has been installed'''
    success = True

    # Print the environment variables for debug purposes
    printer.string("{}environment is:".format(prompt))
    text = subprocess.check_output(["set",], shell=True)
    for line in text.splitlines():
        printer.string("{}{}".format(prompt, line.decode()))

    # Check for the tools on the path
    printer.string("{}checking tools...".format(prompt))
    for item in tools_list:
        if not item["type"] or (item["type"].lower() == sdk.lower()):
            if u_utils.exe_where(item["which_string"], item["hint"],
                                 printer, prompt):
                if item["version_switch"]:
                    u_utils.exe_version(item["which_string"],
                                        item["version_switch"],
                                        printer, prompt)
            else:
                success = False

    return success

def download(connection, guard_time_seconds, hex_path, printer, prompt):
    '''Download the given hex file to an attached NRF52 board'''
    call_list = []

    # Assemble the call list
    call_list.append("nrfjprog")
    call_list.append("-f")
    call_list.append("nrf52")
    call_list.append("--program")
    call_list.append(hex_path)
    call_list.append("--chiperase")
    call_list.append("--verify")
    call_list.append("-r")
    if connection and "debugger" in connection and connection["debugger"]:
        call_list.append("-s")
        call_list.append(connection["debugger"])

    # Print what we're gonna do
    tmp = ""
    for item in call_list:
        tmp += " " + item
    printer.string("{}in directory {} calling{}".         \
                   format(prompt, os.getcwd(), tmp))

    # Call it
    return u_utils.exe_run(call_list, guard_time_seconds, printer, prompt)

def build_gcc(clean, build_subdir, ubxlib_dir,
              defines, printer, prompt, reporter):
    '''Build on GCC'''
    call_list = []
    hex_file_path = None

    # The Nordic Makefile can only handle a
    # single sub-directory name which
    # must be off the directory that
    # Makefile is located in, so need to be
    # in the Makefile directory for building
    # to work
    directory = ubxlib_dir + os.sep + RUNNER_DIR_GCC
    printer.string("{}CD to {}.".format(prompt, directory))

    # Set the Unity path before we change though
    unity_path = os.getcwd() + os.sep + u_utils.UNITY_SUBDIR

    with u_utils.ChangeDir(directory):
        # Clear the output folder if we're not just running
        if not clean or u_utils.deltree(build_subdir,
                                        printer, prompt):
            if defines:
                # Create the CFLAGS string
                cflags = ""
                for idx, define in enumerate(defines):
                    if idx == 0:
                        cflags = "-D" + define
                    else:
                        cflags += " -D" + define
            # Note: when entering things from the command-line
            # if there is more than one CFLAGS parameter then
            # they must be quoted but that is specifically
            # NOT required here as the fact that CFLAGS
            # is passed in as one array entry is sufficient

            # Assemble the whole call list
            call_list.append("make")
            call_list.append("NRF5_PATH=" + NRF5_PATH)
            call_list.append("UNITY_PATH=" + unity_path.replace("\\", "/"))
            if defines:
                call_list.append("CFLAGS=" + cflags)
            call_list.append("OUTPUT_DIRECTORY=" + build_subdir)
            call_list.append("GNU_VERSION=" + GNU_VERSION)
            call_list.append("GNU_PREFIX=" + GNU_PREFIX)
            call_list.append("GNU_INSTALL_ROOT=" + GNU_INSTALL_ROOT)

            # Print what we're gonna do
            tmp = ""
            for item in call_list:
                tmp += " " + item
            printer.string("{}in directory {} calling{}".         \
                           format(prompt, os.getcwd(), tmp))

            # Call make to do the build
            # Set shell to keep Jenkins happy
            if u_utils.exe_run(call_list, BUILD_GUARD_TIME_SECONDS,
                               printer, prompt, shell_cmd=True):
                hex_file_path = os.getcwd() + os.sep + build_subdir +  \
                                os.sep + "nrf52840_xxaa.hex"
        else:
            reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                           u_report.EVENT_FAILED,
                           "unable to clean build directory")

    return hex_file_path

def build_ses(clean, ubxlib_dir, defines,
              printer, prompt, reporter):
    '''Build on SES'''
    call_list = []
    ses_dir = ubxlib_dir + os.sep + RUNNER_DIR_SES
    output_dir = os.getcwd() + os.sep + BUILD_SUBDIR_SES
    too_many_defines = False
    hex_file_path = None

    # Put the path to SES builder at the front of the call list
    call_list.append(SES_PATH + os.sep + SES_NAME)

    # Then the -config switch with the configuration and project name
    call_list.append("-config")
    call_list.append("".join(SES_BUILD_CONFIGURATION))
    call_list.append("".join((ses_dir + os.sep + PROJECT_NAME_SES + ".emProject").
                             replace("\\", "/")))

    # Set the output directory
    call_list.append("-property")
    call_list.append("".join(("build_output_directory=" + output_dir).
                             replace("\\", "/")))
    call_list.append("-property")
    call_list.append("".join(("build_intermediate_directory=" + output_dir +
                              os.sep + "obj").replace("\\", "/")))

    # Add verbose echo otherwise SES builder can be a tad quiet
    call_list.append("-echo")
    call_list.append("-verbose")

    if defines:
        # Create the U_FLAGS entries
        for idx, define in enumerate(defines):
            if idx >= SES_MAX_NUM_DEFINES:
                too_many_defines = True
                string = "{}{} #defines supplied but only"     \
                         " {} are supported by this Segger"    \
                         " Embedded Studio project file".      \
                         format(prompt, len(defines), SES_MAX_NUM_DEFINES)
                reporter.event(u_report.EVENT_TYPE_BUILD,
                               u_report.EVENT_ERROR,
                               string)
                printer.string(string)
                break
            # Note that the quotes which are required on the
            # command-line when including a define of the format
            # BLAH=XXX are not required here.
            call_list.append("-D")
            call_list.append("U_FLAG" + str(idx) + "=" + define)

    if not too_many_defines:
        # Add the NRF5 path and Unity paths,
        # making sure that SES gets "/" as it likes
        # and not "\"
        call_list.append("-D")
        call_list.append("NRF5_PATH=" + "".join(NRF5_PATH.replace("\\", "/")))
        call_list.append("-D")
        call_list.append("UNITY_PATH=" +
                         "".join((os.getcwd() + os.sep + u_utils.UNITY_SUBDIR).
                                 replace("\\", "/")))

        # Clear the output folder if we're not just running
        if not clean or u_utils.deltree(BUILD_SUBDIR_SES,
                                        printer, prompt):
            # Print what we're gonna do
            tmp = ""
            for item in call_list:
                tmp += " " + item
            printer.string("{}in directory {} calling{}".         \
                           format(prompt, os.getcwd(), tmp))

            # Call Segger Embedded Studio builder to do the build
            # Set shell to keep Jenkins happy
            if u_utils.exe_run(call_list, BUILD_GUARD_TIME_SECONDS,
                               printer, prompt, shell_cmd=True):
                hex_file_path = output_dir + os.sep + PROJECT_NAME_SES + ".hex"
        else:
            reporter.event(u_report.EVENT_TYPE_BUILD,
                           u_report.EVENT_ERROR,
                           "unable to clean build directory")

    return hex_file_path

def run(instance, sdk, connection, connection_lock, platform_lock, clean, defines,
        ubxlib_dir, working_dir, printer, reporter, test_report_handle):
    '''Build/run on NRF52'''
    return_value = -1
    hex_file_path = None
    instance_text = u_utils.get_instance_text(instance)
    swo_port = u_utils.JLINK_SWO_PORT

    prompt = PROMPT + instance_text + ": "

    # Print out what we've been told to do
    text = "running NRF52 under SDK " + sdk
    if connection and "debugger" in connection and connection["debugger"]:
        text += ", on JLink debugger serial number " + connection["debugger"]
    if clean:
        text += ", clean build"
    if defines:
        text += ", with #define(s)"
        for idx, define in enumerate(defines):
            if idx == 0:
                text += " \"" + define + "\""
            else:
                text += ", \"" + define + "\""
    if ubxlib_dir:
        text += ", ubxlib directory \"" + ubxlib_dir + "\""
    if working_dir:
        text += ", working directory \"" + working_dir + "\""
    printer.string("{}{}.".format(prompt, text))

    reporter.event(u_report.EVENT_TYPE_BUILD,
                   u_report.EVENT_START,
                   "NRF52/" + sdk)
    # Switch to the working directory
    with u_utils.ChangeDir(working_dir):
        # Check that everything we need is installed
        if check_installation(sdk, TOOLS_LIST, printer, prompt):
            # Fetch Unity
            if u_utils.fetch_repo(u_utils.UNITY_URL,
                                  u_utils.UNITY_SUBDIR,
                                  None, printer, prompt):
                # Do the build
                build_start_time = time()
                if sdk.lower() == "gcc":
                    build_subdir_gcc = BUILD_SUBDIR_PREFIX_GCC + instance_text.replace(".", "_")
                    hex_file_path = build_gcc(clean, build_subdir_gcc, ubxlib_dir,
                                              defines, printer, prompt, reporter)
                elif sdk.lower() == "ses":
                    hex_file_path = build_ses(clean, ubxlib_dir, defines,
                                              printer, prompt, reporter)
                if hex_file_path:
                    # Build succeeded, need to lock a connection to do the download
                    reporter.event(u_report.EVENT_TYPE_BUILD,
                                   u_report.EVENT_PASSED,
                                   "build took {:.0f} second(s)".format(time() -
                                                                        build_start_time))
                    with u_connection.Lock(connection, connection_lock,
                                           CONNECTION_LOCK_GUARD_TIME_SECONDS,
                                           printer, prompt) as locked_connection:
                        if locked_connection:
                            # Do the download
                            # On NRF52 doing a download or starting SWO logging
                            # on more than one platform at a time seems to cause
                            # problems, even though it should be tied to the
                            # serial number of the given debugger on that board,
                            # so lock the platform for this.  Once we've got the
                            # Telnet session opened with the platform it seems
                            # fine to let other downloads/logging-starts happen.
                            with u_utils.Lock(platform_lock, PLATFORM_LOCK_GUARD_TIME_SECONDS,
                                              "platform", printer, prompt) as locked_platform:
                                if locked_platform:
                                    reporter.event(u_report.EVENT_TYPE_DOWNLOAD,
                                                   u_report.EVENT_START)
                                    if download(connection, DOWNLOAD_GUARD_TIME_SECONDS,
                                                hex_file_path, printer, prompt):
                                        reporter.event(u_report.EVENT_TYPE_DOWNLOAD,
                                                       u_report.EVENT_COMPLETE)
                                        reporter.event(u_report.EVENT_TYPE_TEST,
                                                       u_report.EVENT_START)
                                        # I have seen downloads succeeds and then
                                        # the Telnet connection fail, so add a
                                        # little sleep here to make sure one
                                        # has really finished before the other starts
                                        sleep(1)
                                        if connection and "swo_port" in connection:
                                            swo_port = connection["swo_port"]

                                        # With JLink started
                                        RUN_JLINK.append("-RTTTelnetPort")
                                        RUN_JLINK.append(str(swo_port))
                                        if connection and "debugger" in connection and \
                                           connection["debugger"]:
                                            RUN_JLINK.append("-USB")
                                            RUN_JLINK.append(connection["debugger"])
                                        with u_utils.ExeRun(RUN_JLINK, printer, prompt):
                                            # Open the Telnet port to JLink
                                            # to get the debug output
                                            telnet_handle = u_utils.open_telnet(swo_port,
                                                                                printer, prompt)
                                            if telnet_handle is not None:
                                                # Once we've got a Telnet session running
                                                # it is OK to release the platform lock again.
                                                platform_lock.release()
                                                # Monitor progress
                                                return_value = u_monitor.    \
                                                               main(telnet_handle,
                                                                    u_monitor.CONNECTION_TELNET,
                                                                    RUN_GUARD_TIME_SECONDS,
                                                                    RUN_INACTIVITY_TIME_SECONDS,
                                                                    instance, printer, reporter,
                                                                    test_report_handle)
                                                telnet_handle.close()
                                            else:
                                                reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                                                               u_report.EVENT_FAILED,
                                                               "unable to open SWO port " +  \
                                                               str(swo_port))
                                        if return_value == 0:
                                            reporter.event(u_report.EVENT_TYPE_TEST,
                                                           u_report.EVENT_COMPLETE)
                                        else:
                                            reporter.event(u_report.EVENT_TYPE_TEST,
                                                           u_report.EVENT_FAILED)
                                    else:
                                        reporter.event(u_report.EVENT_TYPE_DOWNLOAD,
                                                       u_report.EVENT_FAILED,
                                                       "check debug log for details")
                                else:
                                    reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                                                   u_report.EVENT_FAILED,
                                                   "unable to lock the platform")
                        else:
                            reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                                           u_report.EVENT_FAILED,
                                           "unable to lock a connection")
                else:
                    return_value = 1
                    reporter.event(u_report.EVENT_TYPE_BUILD,
                                   u_report.EVENT_FAILED,
                                   "check debug log for details")
            else:
                reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                               u_report.EVENT_FAILED,
                               "unable to fetch Unity")
        else:
            reporter.event(u_report.EVENT_TYPE_INFRASTRUCTURE,
                           u_report.EVENT_FAILED,
                           "there is a problem with the tools installation for NRF52")

    return return_value
