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

#ifndef _U_PORT_CLIB_PLATFORM_SPECIFIC_H_
#define _U_PORT_CLIB_PLATFORM_SPECIFIC_H_

/** @file
 * @brief Implementations of C library functions not available on this
 * platform.
 */

#ifdef U_CFG_DISABLE_FLOATING_POINT
/** If floating point is not required, switch to the integer
 * versions of the stdio library functions.
 * Note: with floating point disabled the ubxlib code will not
 * be able to log floating point values (i.e. %f or %d types)
 * and will not use maths functions (e.g. pow(), log10()).
 * Any ubxlib APIs that rely on floating point functionality
 * will return an error.
 */
#define snprintf sniprintf
#define printf iprintf
#define vprintf viprintf
#define sscanf siscanf
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* ----------------------------------------------------------------
 * COMPILE-TIME MACROS
 * -------------------------------------------------------------- */

/* ----------------------------------------------------------------
 * TYPES
 * -------------------------------------------------------------- */

/* ----------------------------------------------------------------
 * FUNCTIONS
 * -------------------------------------------------------------- */

#ifdef __cplusplus
}
#endif

#endif // _U_PORT_CLIB_PLATFORM_SPECIFIC_H_

// End of file
