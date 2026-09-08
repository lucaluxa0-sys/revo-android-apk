#ifndef OS_H
#define OS_H

#if !defined(IS_MACOSX) && defined(__APPLE__) && defined(__MACH__)
	#define IS_MACOSX
	#include <dlfcn.h>
    #include <CoreFoundation/CoreFoundation.h>
    #include <CoreGraphics/CoreGraphics.h>
    #include <ApplicationServices/ApplicationServices.h>
    #include <IOKit/graphics/IOGraphicsTypes.h>
#endif /* IS_MACOSX */

#if !defined(IS_WINDOWS) && (defined(WIN32) || defined(_WIN32) || \
                            defined(__WIN32__) || defined(__WINDOWS__) || defined(__CYGWIN__))
	#define IS_WINDOWS
#endif /* IS_WINDOWS */
#endif