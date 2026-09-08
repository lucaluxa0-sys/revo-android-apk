## OpenCV Bindings

This directory contains stripped-down bindings extracted from GoCV. You must download the OpenCV [source](https://opencv.org/releases/) code and build it yourself using the follow commands.

* For MacOS, Xcode version 15.4 or lower must be installed.
* For Windows, [MinGW](https://www.mingw-w64.org/downloads/) must be installed at the C:\ directory.

### Build Instructions

MacOS:

```bash
cmake -G "Unix Makefiles" -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 -DWITH_JPEG=OFF -DWITH_TIFF=OFF -DWITH_WEBP=OFF -DWITH_OPENJPEG=OFF -DWITH_JASPER=OFF -DWITH_OPENEXR=OFF -DWITH_FFMPEG=OFF -DWITH_GSTREAMER=OFF -DWITH_MSFMF=OFF -DBUILD_LIST=features2d,imgcodecs,flann -DWITH_OPENCL=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release -DOPENCV_VS_VERSIONINFO_SKIP=1 -DCMAKE_INSTALL_PREFIX=~/go/src/github.com/nosyliam/revolution/opencv ..
```

Windows:

```bash
cmake -G "MinGW Makefiles" -D"CMAKE_MAKE_PROGRAM:PATH=C:\mingw64\bin\mingw32-make.exe" -DWITH_JPEG=OFF -DWITH_TIFF=OFF -DWITH_WEBP=OFF -DWITH_OPENJPEG=OFF -DWITH_JASPER=OFF -DWITH_OPENEXR=OFF -DWITH_FFMPEG=OFF -DWITH_GSTREAMER=OFF -DWITH_MSFMF=OFF -DBUILD_LIST="features2d,imgcodecs,flann" -DWITH_OPENCL=OFF -DBUILD_SHARED_LIBS=OFF -DCMAKE_BUILD_TYPE=Release -DOPENCV_VS_VERSIONINFO_SKIP=1 -DCMAKE_INSTALL_PREFIX="~/go/src/github.com/nosyliam/revolution/opencv" ..
```