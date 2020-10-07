/*
 * Copyright 2020 u-blox Ltd
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/** @file
 * @brief The application entry point for the STM32F4 platform.  Starts
 * the platform and calls Unity to run the selected examples/tests.
 */

#ifdef U_CFG_OVERRIDE
# include "u_cfg_override.h" // For a customer's configuration override
#endif

#include "stddef.h"    // NULL, size_t etc.
#include "stdint.h"    // int32_t etc.
#include "stdbool.h"

#include "u_cfg_sw.h"
#include "u_cfg_os_platform_specific.h"
#include "u_cfg_app_platform_specific.h"
#include "u_cfg_test_platform_specific.h"
#include "u_error_common.h"
#include "u_port.h"
#include "u_port_debug.h"
#include "u_port_gpio.h"

#include "u_runner.h"

#include "cmsis_os.h"

#include "assert.h"

/* ----------------------------------------------------------------
 * COMPILE-TIME MACROS
 * -------------------------------------------------------------- */

/* ----------------------------------------------------------------
 * TYPES
 * -------------------------------------------------------------- */

/* ----------------------------------------------------------------
 * VARIABLES
 * -------------------------------------------------------------- */

/* ----------------------------------------------------------------
 * STATIC FUNCTIONS
 * -------------------------------------------------------------- */

// The task within which examples and tests are run.
static void appTask(void *pParam)
{
    (void) pParam;
#if (U_CFG_APP_PIN_C030_ENABLE_3V3 >= 0) || (U_CFG_APP_PIN_CELL_RESET >= 0)
    uPortGpioConfig_t gpioConfig = U_PORT_GPIO_CONFIG_DEFAULT;
#endif

    uPortInit();

#if U_CFG_APP_PIN_C030_ENABLE_3V3 >= 0
    // Enable power to 3V3 rail for the C030 board
    gpioConfig.pin = U_CFG_APP_PIN_C030_ENABLE_3V3;
    gpioConfig.driveMode = U_PORT_GPIO_DRIVE_MODE_OPEN_DRAIN;
    gpioConfig.direction = U_PORT_GPIO_DIRECTION_OUTPUT;
    uPortGpioConfig(&gpioConfig);
    uPortGpioSet(U_CFG_APP_PIN_C030_ENABLE_3V3, 1);
#endif
#if U_CFG_APP_PIN_CELL_RESET >= 0
    // Set reset high (i.e. not reset) if it is connected
    gpioConfig.pin = U_CFG_APP_PIN_CELL_RESET;
    gpioConfig.driveMode = U_PORT_GPIO_DRIVE_MODE_NORMAL;
    gpioConfig.direction = U_PORT_GPIO_DIRECTION_OUTPUT;
    uPortGpioConfig(&gpioConfig);
    uPortGpioSet(U_CFG_APP_PIN_CELL_RESET, 1);
#endif

    uPortLog("\n\nU_APP: application task started.\n");

    // Call Unity hook
    UNITY_BEGIN();

    uPortLog("U_APP: functions available:\n\n");
    uRunnerPrintAll("U_APP: ");
#ifdef U_CFG_APP_FILTER
    uPortLog("U_APP: running functions that begin with \"%s\".\n",
             U_PORT_STRINGIFY_QUOTED(U_CFG_APP_FILTER));
    uRunnerRunFiltered(U_PORT_STRINGIFY_QUOTED(U_CFG_APP_FILTER),
                       "U_APP: ");
#else
    uPortLog("U_APP: running all functions.\n");
    uRunnerRunAll("U_APP: ");
#endif

    // Call Unity hook
    UNITY_END();

    uPortLog("\n\nU_APP: application task ended.\n");
    uPortDeinit();

    while (1) {}
}

/* ----------------------------------------------------------------
 * PUBLIC FUNCTIONS
 * -------------------------------------------------------------- */

// Unity setUp() function.
void setUp(void)
{
    // Nothing to do
}

// Unity tearDown() function.
void tearDown(void)
{
    // Nothing to do
}

void testFail(void)
{
    // Nothing to do
}

// Entry point
int main(void)
{
    // Execute the application task
    uPortPlatformStart(appTask, NULL,
                       U_CFG_OS_APP_TASK_STACK_SIZE_BYTES,
                       U_CFG_OS_APP_TASK_PRIORITY);

    // Should never get here
    assert(false);

    return 0;
}

// End of file
