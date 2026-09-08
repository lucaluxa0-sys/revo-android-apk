#include "features2d.h"

BFMatcher BFMatcher_Create() {
    return new cv::Ptr<cv::BFMatcher>(cv::BFMatcher::create());
}

BFMatcher BFMatcher_CreateWithParams(int normType, bool crossCheck) {
    return new cv::Ptr<cv::BFMatcher>(cv::BFMatcher::create(normType, crossCheck));
}

void BFMatcher_Close(BFMatcher b) {
    delete b;
}

struct DMatches BFMatcher_Match(BFMatcher b, Mat query, Mat train) {
    std::vector<cv::DMatch> matches;
    (*b)->match(*query, *train, matches);

    DMatch *dmatches = new DMatch[matches.size()];
    for (size_t i = 0; i < matches.size(); ++i) {
        DMatch dmatch = {matches[i].queryIdx, matches[i].trainIdx, matches[i].imgIdx, matches[i].distance};
        dmatches[i] = dmatch;
    }
    DMatches ret = {dmatches, (int) matches.size()};
    return ret;
}

struct MultiDMatches BFMatcher_KnnMatch(BFMatcher b, Mat query, Mat train, int k) {
    std::vector< std::vector<cv::DMatch> > matches;
    (*b)->knnMatch(*query, *train, matches, k);

    DMatches *dms = new DMatches[matches.size()];
    for (size_t i = 0; i < matches.size(); ++i) {
        DMatch *dmatches = new DMatch[matches[i].size()];
        for (size_t j = 0; j < matches[i].size(); ++j) {
            DMatch dmatch = {matches[i][j].queryIdx, matches[i][j].trainIdx, matches[i][j].imgIdx,
                             matches[i][j].distance};
            dmatches[j] = dmatch;
        }
        dms[i] = {dmatches, (int) matches[i].size()};
    }
    MultiDMatches ret = {dms, (int) matches.size()};
    return ret;
}

struct MultiDMatches BFMatcher_KnnMatchWithParams(BFMatcher b, Mat query, Mat train, int k, Mat mask, bool compactResult) {
    std::vector< std::vector<cv::DMatch> > matches;
    (*b)->knnMatch(*query, *train, matches, k, *mask, compactResult);

    DMatches *dms = new DMatches[matches.size()];
    for (size_t i = 0; i < matches.size(); ++i) {
        DMatch *dmatches = new DMatch[matches[i].size()];
        for (size_t j = 0; j < matches[i].size(); ++j) {
            DMatch dmatch = {matches[i][j].queryIdx, matches[i][j].trainIdx, matches[i][j].imgIdx,
                             matches[i][j].distance};
            dmatches[j] = dmatch;
        }
        dms[i] = {dmatches, (int) matches[i].size()};
    }
    MultiDMatches ret = {dms, (int) matches.size()};
    return ret;
}

FlannBasedMatcher FlannBasedMatcher_Create() {
    return new cv::Ptr<cv::FlannBasedMatcher>(cv::FlannBasedMatcher::create());
}

void FlannBasedMatcher_Close(FlannBasedMatcher f) {
    delete f;
}

struct MultiDMatches FlannBasedMatcher_KnnMatch(FlannBasedMatcher f, Mat query, Mat train, int k) {
    std::vector< std::vector<cv::DMatch> > matches;
    (*f)->knnMatch(*query, *train, matches, k);

    DMatches *dms = new DMatches[matches.size()];
    for (size_t i = 0; i < matches.size(); ++i) {
        DMatch *dmatches = new DMatch[matches[i].size()];
        for (size_t j = 0; j < matches[i].size(); ++j) {
            DMatch dmatch = {matches[i][j].queryIdx, matches[i][j].trainIdx, matches[i][j].imgIdx,
                             matches[i][j].distance};
            dmatches[j] = dmatch;
        }
        dms[i] = {dmatches, (int) matches[i].size()};
    }
    MultiDMatches ret = {dms, (int) matches.size()};
    return ret;
}

struct MultiDMatches FlannBasedMatcher_KnnMatchWithParams(FlannBasedMatcher f, Mat query, Mat train, int k, Mat mask, bool compactResult) {
    std::vector< std::vector<cv::DMatch> > matches;
    (*f)->knnMatch(*query, *train, matches, k, *mask, compactResult);

    DMatches *dms = new DMatches[matches.size()];
    for (size_t i = 0; i < matches.size(); ++i) {
        DMatch *dmatches = new DMatch[matches[i].size()];
        for (size_t j = 0; j < matches[i].size(); ++j) {
            DMatch dmatch = {matches[i][j].queryIdx, matches[i][j].trainIdx, matches[i][j].imgIdx,
                             matches[i][j].distance};
            dmatches[j] = dmatch;
        }
        dms[i] = {dmatches, (int) matches[i].size()};
    }
    MultiDMatches ret = {dms, (int) matches.size()};
    return ret;
}

void DrawKeyPoints(Mat src, struct KeyPoints kp, Mat dst, Scalar s, int flags) {
        std::vector<cv::KeyPoint> keypts;
        cv::KeyPoint keypt;

        for (int i = 0; i < kp.length; ++i) {
                keypt = cv::KeyPoint(kp.keypoints[i].x, kp.keypoints[i].y,
                                kp.keypoints[i].size, kp.keypoints[i].angle, kp.keypoints[i].response,
                                kp.keypoints[i].octave, kp.keypoints[i].classID);
                keypts.push_back(keypt);
        }

        cv::Scalar color = cv::Scalar(s.val1, s.val2, s.val3, s.val4);

        cv::drawKeypoints(*src, keypts, *dst, color, static_cast<cv::DrawMatchesFlags>(flags));
}

SIFT SIFT_Create() {
    // TODO: params
    return new cv::Ptr<cv::SIFT>(cv::SIFT::create());
}

SIFT SIFT_CreateWithParams(int nfeatures, int nOctaveLayers, double contrastThreshold, double edgeThreshold, double sigma) {
    return new cv::Ptr<cv::SIFT>(cv::SIFT::create(nfeatures, nOctaveLayers, contrastThreshold, edgeThreshold, sigma));
}


void SIFT_Close(SIFT d) {
    delete d;
}

struct KeyPoints SIFT_Detect(SIFT d, Mat src) {
    std::vector<cv::KeyPoint> detected;
    (*d)->detect(*src, detected);

    KeyPoint* kps = new KeyPoint[detected.size()];

    for (size_t i = 0; i < detected.size(); ++i) {
        KeyPoint k = {detected[i].pt.x, detected[i].pt.y, detected[i].size, detected[i].angle,
                      detected[i].response, detected[i].octave, detected[i].class_id
                     };
        kps[i] = k;
    }

    KeyPoints ret = {kps, (int)detected.size()};
    return ret;
}

struct KeyPoints SIFT_Compute(SIFT d, Mat src, struct KeyPoints kp, Mat desc) {
    std::vector<cv::KeyPoint> computed;
    for (size_t i = 0; i < kp.length; i++) {
        cv::KeyPoint k = cv::KeyPoint(kp.keypoints[i].x, kp.keypoints[i].y,
            kp.keypoints[i].size, kp.keypoints[i].angle, kp.keypoints[i].response,
            kp.keypoints[i].octave, kp.keypoints[i].classID);
        computed.push_back(k);
    }

    (*d)->compute(*src, computed, *desc);

    KeyPoint* kps = new KeyPoint[computed.size()];

    for (size_t i = 0; i < computed.size(); ++i) {
        KeyPoint k = {computed[i].pt.x, computed[i].pt.y, computed[i].size, computed[i].angle,
                      computed[i].response, computed[i].octave, computed[i].class_id
                     };
        kps[i] = k;
    }

    KeyPoints ret = {kps, (int)computed.size()};
    return ret;
}

struct KeyPoints SIFT_DetectAndCompute(SIFT d, Mat src, Mat mask, Mat desc) {
    std::vector<cv::KeyPoint> detected;
    (*d)->detectAndCompute(*src, *mask, detected, *desc);

    KeyPoint* kps = new KeyPoint[detected.size()];

    for (size_t i = 0; i < detected.size(); ++i) {
        KeyPoint k = {detected[i].pt.x, detected[i].pt.y, detected[i].size, detected[i].angle,
                      detected[i].response, detected[i].octave, detected[i].class_id
                     };
        kps[i] = k;
    }

    KeyPoints ret = {kps, (int)detected.size()};
    return ret;
}

void DrawMatches(Mat img1, struct KeyPoints kp1, Mat img2, struct KeyPoints kp2, struct DMatches matches1to2, Mat outImg, const Scalar matchesColor, const Scalar pointColor, struct ByteArray matchesMask, int flags) {
    std::vector<cv::KeyPoint> kp1vec, kp2vec;
    cv::KeyPoint keypt;

    for (int i = 0; i < kp1.length; ++i) {
        keypt = cv::KeyPoint(kp1.keypoints[i].x, kp1.keypoints[i].y,
                            kp1.keypoints[i].size, kp1.keypoints[i].angle, kp1.keypoints[i].response,
                            kp1.keypoints[i].octave, kp1.keypoints[i].classID);
        kp1vec.push_back(keypt);
    }

    for (int i = 0; i < kp2.length; ++i) {
        keypt = cv::KeyPoint(kp2.keypoints[i].x, kp2.keypoints[i].y,
                            kp2.keypoints[i].size, kp2.keypoints[i].angle, kp2.keypoints[i].response,
                            kp2.keypoints[i].octave, kp2.keypoints[i].classID);
        kp2vec.push_back(keypt);
    }

    cv::Scalar cvmatchescolor = cv::Scalar(matchesColor.val1, matchesColor.val2, matchesColor.val3, matchesColor.val4);
    cv::Scalar cvpointcolor = cv::Scalar(pointColor.val1, pointColor.val2, pointColor.val3, pointColor.val4);
    
    std::vector<cv::DMatch> dmatchvec;
    cv::DMatch dm;

    for (int i = 0; i < matches1to2.length; i++) {
        dm = cv::DMatch(matches1to2.dmatches[i].queryIdx, matches1to2.dmatches[i].trainIdx,
                        matches1to2.dmatches[i].imgIdx, matches1to2.dmatches[i].distance);
        dmatchvec.push_back(dm);
    }

    std::vector<char> maskvec;

    for (int i = 0; i < matchesMask.length; i++) {
        maskvec.push_back(matchesMask.data[i]);
    }

    cv::drawMatches(*img1, kp1vec, *img2, kp2vec, dmatchvec, *outImg, cvmatchescolor, cvpointcolor, maskvec, static_cast<cv::DrawMatchesFlags>(flags));
}
