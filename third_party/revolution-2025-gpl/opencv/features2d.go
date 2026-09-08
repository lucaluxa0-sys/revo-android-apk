package opencv

/*
#include <stdlib.h>
#include "features2d.h"
*/
import "C"
import (
	"image/color"
	"io"
	"reflect"
	"unsafe"
)

type Feature2DDetector interface {
	Detect(src Mat) []KeyPoint
}

type Feature2DComputer interface {
	Compute(src Mat, mask Mat, kps []KeyPoint) ([]KeyPoint, Mat)
}

type Feature2DDetectComputer interface {
	DetectAndCompute(src Mat, mask Mat) ([]KeyPoint, Mat)
}

type Feature2D interface {
	io.Closer
	Feature2DDetector
	Feature2DComputer
	Feature2DDetectComputer
}

// getKeyPoints returns a slice of KeyPoint given a pointer to a C.KeyPoints
func getKeyPoints(ret C.KeyPoints) []KeyPoint {
	cArray := ret.keypoints
	length := int(ret.length)
	hdr := reflect.SliceHeader{
		Data: uintptr(unsafe.Pointer(cArray)),
		Len:  length,
		Cap:  length,
	}
	s := *(*[]C.KeyPoint)(unsafe.Pointer(&hdr))

	keys := make([]KeyPoint, length)
	for i, r := range s {
		keys[i] = KeyPoint{float64(r.x), float64(r.y), float64(r.size), float64(r.angle), float64(r.response),
			int(r.octave), int(r.classID)}
	}
	return keys
}

// BFMatcher is a wrapper around the the cv::BFMatcher algorithm
type BFMatcher struct {
	// C.BFMatcher
	p unsafe.Pointer
}

// NewBFMatcher returns a new BFMatcher
//
// For further details, please see:
// https://docs.opencv.org/master/d3/da1/classcv_1_1BFMatcher.html#abe0bb11749b30d97f60d6ade665617bd
func NewBFMatcher() BFMatcher {
	return BFMatcher{p: unsafe.Pointer(C.BFMatcher_Create())}
}

// NewBFMatcherWithParams creates a new BFMatchers but allows setting parameters
// to values other than just the defaults.
//
// For further details, please see:
// https://docs.opencv.org/master/d3/da1/classcv_1_1BFMatcher.html#abe0bb11749b30d97f60d6ade665617bd
func NewBFMatcherWithParams(normType NormType, crossCheck bool) BFMatcher {
	return BFMatcher{p: unsafe.Pointer(C.BFMatcher_CreateWithParams(C.int(normType), C.bool(crossCheck)))}
}

// Close BFMatcher
func (b *BFMatcher) Close() error {
	C.BFMatcher_Close((C.BFMatcher)(b.p))
	b.p = nil
	return nil
}

// Match Finds the best match for each descriptor from a query set.
//
// For further details, please see:
// https://docs.opencv.org/4.x/db/d39/classcv_1_1DescriptorMatcher.html#a0f046f47b68ec7074391e1e85c750cba
func (b *BFMatcher) Match(query, train Mat) []DMatch {
	ret := C.BFMatcher_Match((C.BFMatcher)(b.p), query.p, train.p)
	defer C.DMatches_Close(ret)

	return getDMatches(ret)
}

// KnnMatch Finds the k best matches for each descriptor from a query set.
//
// For further details, please see:
// https://docs.opencv.org/master/db/d39/classcv_1_1DescriptorMatcher.html#aa880f9353cdf185ccf3013e08210483a
func (b *BFMatcher) KnnMatch(query, train Mat, k int) [][]DMatch {
	ret := C.BFMatcher_KnnMatch((C.BFMatcher)(b.p), query.p, train.p, C.int(k))
	defer C.MultiDMatches_Close(ret)

	return getMultiDMatches(ret)
}

// FlannBasedMatcher is a wrapper around the the cv::FlannBasedMatcher algorithm
type FlannBasedMatcher struct {
	// C.FlannBasedMatcher
	p unsafe.Pointer
}

// NewFlannBasedMatcher returns a new FlannBasedMatcher
//
// For further details, please see:
// https://docs.opencv.org/master/dc/de2/classcv_1_1FlannBasedMatcher.html#ab9114a6471e364ad221f89068ca21382
func NewFlannBasedMatcher() FlannBasedMatcher {
	return FlannBasedMatcher{p: unsafe.Pointer(C.FlannBasedMatcher_Create())}
}

// Close FlannBasedMatcher
func (f *FlannBasedMatcher) Close() error {
	C.FlannBasedMatcher_Close((C.FlannBasedMatcher)(f.p))
	f.p = nil
	return nil
}

// KnnMatch Finds the k best matches for each descriptor from a query set.
//
// For further details, please see:
// https://docs.opencv.org/master/db/d39/classcv_1_1DescriptorMatcher.html#aa880f9353cdf185ccf3013e08210483a
func (f *FlannBasedMatcher) KnnMatch(query, train Mat, k int) [][]DMatch {
	ret := C.FlannBasedMatcher_KnnMatch((C.FlannBasedMatcher)(f.p), query.p, train.p, C.int(k))
	defer C.MultiDMatches_Close(ret)

	return getMultiDMatches(ret)
}

func getMultiDMatches(ret C.MultiDMatches) [][]DMatch {
	cArray := ret.dmatches
	length := int(ret.length)
	hdr := reflect.SliceHeader{
		Data: uintptr(unsafe.Pointer(cArray)),
		Len:  length,
		Cap:  length,
	}
	s := *(*[]C.DMatches)(unsafe.Pointer(&hdr))

	keys := make([][]DMatch, length)
	for i := range s {
		keys[i] = getDMatches(C.MultiDMatches_get(ret, C.int(i)))
	}
	return keys
}

func getDMatches(ret C.DMatches) []DMatch {
	cArray := ret.dmatches
	length := int(ret.length)
	hdr := reflect.SliceHeader{
		Data: uintptr(unsafe.Pointer(cArray)),
		Len:  length,
		Cap:  length,
	}
	s := *(*[]C.DMatch)(unsafe.Pointer(&hdr))

	keys := make([]DMatch, length)
	for i, r := range s {
		keys[i] = DMatch{int(r.queryIdx), int(r.trainIdx), int(r.imgIdx),
			float64(r.distance)}
	}
	return keys
}

// DrawMatchesFlag are the flags setting drawing feature
//
// For further details please see:
// https://docs.opencv.org/master/de/d30/structcv_1_1DrawMatchesFlags.html
type DrawMatchesFlag int

const (
	// DrawDefault creates new image and for each keypoint only the center point will be drawn
	DrawDefault DrawMatchesFlag = 0
	// DrawOverOutImg draws matches on existing content of image
	DrawOverOutImg DrawMatchesFlag = 1
	// NotDrawSinglePoints will not draw single points
	NotDrawSinglePoints DrawMatchesFlag = 2
	// DrawRichKeyPoints draws the circle around each keypoint with keypoint size and orientation
	DrawRichKeyPoints DrawMatchesFlag = 3
)

// DrawKeyPoints draws keypoints
//
// For further details please see:
// https://docs.opencv.org/master/d4/d5d/group__features2d__draw.html#gab958f8900dd10f14316521c149a60433
func DrawKeyPoints(src Mat, keyPoints []KeyPoint, dst *Mat, color color.RGBA, flag DrawMatchesFlag) {
	cKeyPointArray := make([]C.struct_KeyPoint, len(keyPoints))

	for i, kp := range keyPoints {
		cKeyPointArray[i].x = C.double(kp.X)
		cKeyPointArray[i].y = C.double(kp.Y)
		cKeyPointArray[i].size = C.double(kp.Size)
		cKeyPointArray[i].angle = C.double(kp.Angle)
		cKeyPointArray[i].response = C.double(kp.Response)
		cKeyPointArray[i].octave = C.int(kp.Octave)
		cKeyPointArray[i].classID = C.int(kp.ClassID)
	}

	cKeyPoints := C.struct_KeyPoints{
		keypoints: (*C.struct_KeyPoint)(&cKeyPointArray[0]),
		length:    (C.int)(len(keyPoints)),
	}

	scalar := C.struct_Scalar{
		val1: C.double(color.B),
		val2: C.double(color.G),
		val3: C.double(color.R),
		val4: C.double(color.A),
	}

	C.DrawKeyPoints(src.p, cKeyPoints, dst.p, scalar, C.int(flag))
}

// SIFT is a wrapper around the cv::SIFT algorithm.
// Due to the patent having expired, this is now in the main OpenCV code modules.
type SIFT struct {
	// C.SIFT
	p unsafe.Pointer
}

var _ Feature2D = (*SIFT)(nil)

// NewSIFT returns a new SIFT algorithm.
//
// For further details, please see:
// https://docs.opencv.org/master/d5/d3c/classcv_1_1xfeatures2d_1_1SIFT.html
func NewSIFT() SIFT {
	return SIFT{p: unsafe.Pointer(C.SIFT_Create())}
}

func NewSIFTWithParams(nfeatures *int, nOctaveLayers *int, contrastThreshold *float64, edgeThreshold *float64, sigma *float64) SIFT {
	numFeatures := 0
	if nfeatures != nil {
		numFeatures = *nfeatures
	}

	numOctaveLayers := 3

	if nOctaveLayers != nil {
		numOctaveLayers = *nOctaveLayers
	}

	var numContrastThreshold float64 = 0.04

	if contrastThreshold != nil {
		numContrastThreshold = *contrastThreshold
	}

	var numEdgeThreshold float64 = 10

	if edgeThreshold != nil {
		numEdgeThreshold = *edgeThreshold
	}

	var numSigma float64 = 1.6

	if sigma != nil {
		numSigma = *sigma
	}

	return SIFT{p: unsafe.Pointer(C.SIFT_CreateWithParams(C.int(numFeatures), C.int(numOctaveLayers), C.double(numContrastThreshold), C.double(numEdgeThreshold), C.double(numSigma)))}
}

// Close SIFT.
func (d *SIFT) Close() error {
	C.SIFT_Close((C.SIFT)(d.p))
	d.p = nil
	return nil
}

// Detect keypoints in an image using SIFT.
//
// For further details, please see:
// https://docs.opencv.org/master/d0/d13/classcv_1_1Feature2D.html#aa4e9a7082ec61ebc108806704fbd7887
func (d *SIFT) Detect(src Mat) []KeyPoint {
	ret := C.SIFT_Detect((C.SIFT)(d.p), C.Mat(src.Ptr()))
	defer C.KeyPoints_Close(ret)

	return getKeyPoints(ret)
}

// Compute keypoints in an image using SIFT.
//
// For further details, please see:
// https://docs.opencv.org/4.x/d0/d13/classcv_1_1Feature2D.html#ab3cce8d56f4fc5e1d530b5931e1e8dc0
func (d *SIFT) Compute(src Mat, mask Mat, kps []KeyPoint) ([]KeyPoint, Mat) {
	desc := NewMat()
	kp2arr := make([]C.struct_KeyPoint, len(kps))
	for i, kp := range kps {
		kp2arr[i].x = C.double(kp.X)
		kp2arr[i].y = C.double(kp.Y)
		kp2arr[i].size = C.double(kp.Size)
		kp2arr[i].angle = C.double(kp.Angle)
		kp2arr[i].response = C.double(kp.Response)
		kp2arr[i].octave = C.int(kp.Octave)
		kp2arr[i].classID = C.int(kp.ClassID)
	}
	cKeyPoints := C.struct_KeyPoints{
		keypoints: (*C.struct_KeyPoint)(&kp2arr[0]),
		length:    (C.int)(len(kps)),
	}

	ret := C.SIFT_Compute((C.SIFT)(d.p), src.p, cKeyPoints, desc.p)
	defer C.KeyPoints_Close(ret)

	return getKeyPoints(ret), desc
}

// DetectAndCompute detects and computes keypoints in an image using SIFT.
//
// For further details, please see:
// https://docs.opencv.org/master/d0/d13/classcv_1_1Feature2D.html#a8be0d1c20b08eb867184b8d74c15a677
func (d *SIFT) DetectAndCompute(src Mat, mask Mat) ([]KeyPoint, Mat) {
	desc := NewMat()
	ret := C.SIFT_DetectAndCompute((C.SIFT)(d.p), C.Mat(src.Ptr()), C.Mat(mask.Ptr()),
		C.Mat(desc.Ptr()))
	defer C.KeyPoints_Close(ret)

	return getKeyPoints(ret), desc
}

// DrawMatches draws matches on combined train and querry images.
//
// For further details, please see:
// https://docs.opencv.org/master/d4/d5d/group__features2d__draw.html#gad8f463ccaf0dc6f61083abd8717c261a
func DrawMatches(img1 Mat, kp1 []KeyPoint, img2 Mat, kp2 []KeyPoint, matches1to2 []DMatch, outImg *Mat, matchColor color.RGBA, singlePointColor color.RGBA, matchesMask []byte, flags DrawMatchesFlag) {
	kp1arr := make([]C.struct_KeyPoint, len(kp1))
	kp2arr := make([]C.struct_KeyPoint, len(kp2))

	for i, kp := range kp1 {
		kp1arr[i].x = C.double(kp.X)
		kp1arr[i].y = C.double(kp.Y)
		kp1arr[i].size = C.double(kp.Size)
		kp1arr[i].angle = C.double(kp.Angle)
		kp1arr[i].response = C.double(kp.Response)
		kp1arr[i].octave = C.int(kp.Octave)
		kp1arr[i].classID = C.int(kp.ClassID)
	}

	for i, kp := range kp2 {
		kp2arr[i].x = C.double(kp.X)
		kp2arr[i].y = C.double(kp.Y)
		kp2arr[i].size = C.double(kp.Size)
		kp2arr[i].angle = C.double(kp.Angle)
		kp2arr[i].response = C.double(kp.Response)
		kp2arr[i].octave = C.int(kp.Octave)
		kp2arr[i].classID = C.int(kp.ClassID)
	}

	cKeyPoints1 := C.struct_KeyPoints{
		keypoints: (*C.struct_KeyPoint)(&kp1arr[0]),
		length:    (C.int)(len(kp1)),
	}

	cKeyPoints2 := C.struct_KeyPoints{
		keypoints: (*C.struct_KeyPoint)(&kp2arr[0]),
		length:    (C.int)(len(kp2)),
	}

	dMatchArr := make([]C.struct_DMatch, len(matches1to2))

	for i, dm := range matches1to2 {
		dMatchArr[i].queryIdx = C.int(dm.QueryIdx)
		dMatchArr[i].trainIdx = C.int(dm.TrainIdx)
		dMatchArr[i].imgIdx = C.int(dm.ImgIdx)
		dMatchArr[i].distance = C.float(dm.Distance)
	}

	cDMatches := C.struct_DMatches{
		dmatches: (*C.struct_DMatch)(&dMatchArr[0]),
		length:   (C.int)(len(matches1to2)),
	}

	scalarMatchColor := C.struct_Scalar{
		val1: C.double(matchColor.R),
		val2: C.double(matchColor.G),
		val3: C.double(matchColor.B),
		val4: C.double(matchColor.A),
	}

	scalarPointColor := C.struct_Scalar{
		val1: C.double(singlePointColor.B),
		val2: C.double(singlePointColor.G),
		val3: C.double(singlePointColor.R),
		val4: C.double(singlePointColor.A),
	}

	mask := make([]C.char, len(matchesMask))

	cByteArray := C.struct_ByteArray{
		length: (C.int)(len(matchesMask)),
	}

	if len(matchesMask) > 0 {
		cByteArray = C.struct_ByteArray{
			data:   (*C.char)(&mask[0]),
			length: (C.int)(len(matchesMask)),
		}
	}

	C.DrawMatches(img1.p, cKeyPoints1, img2.p, cKeyPoints2, cDMatches, outImg.p, scalarMatchColor, scalarPointColor, cByteArray, C.int(flags))
}
