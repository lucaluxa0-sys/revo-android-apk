// CaptureController.m
#import "CaptureController.h"
#import <Accelerate/Accelerate.h>
#import <AVFoundation/AVFoundation.h>

@interface StreamOutput : NSObject <SCStreamOutput>
@property (nonatomic, weak) CaptureController *owner;
@end

@implementation StreamOutput

- (void)stream:(SCStream *)stream
didOutputSampleBuffer:(CMSampleBufferRef)sampleBuffer
       ofType:(SCStreamOutputType)type
{
    if (!CMSampleBufferIsValid(sampleBuffer) ||
        CMSampleBufferGetNumSamples(sampleBuffer) == 0) {
        return;
    }

    CVPixelBufferRef pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer);
    if (!pixelBuffer) return;

    CVPixelBufferLockBaseAddress(pixelBuffer, kCVPixelBufferLock_ReadOnly);

    size_t fullWidth   = CVPixelBufferGetWidth(pixelBuffer);
    size_t fullHeight  = CVPixelBufferGetHeight(pixelBuffer);
    size_t bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer);
    unsigned char *base = CVPixelBufferGetBaseAddress(pixelBuffer);

    size_t fullLen = bytesPerRow * fullHeight;
    unsigned char *bgraData = malloc(fullLen);
    memcpy(bgraData, base, fullLen);
    CVPixelBufferUnlockBaseAddress(pixelBuffer, kCVPixelBufferLock_ReadOnly);

    uint8_t *rgbaData = malloc(fullLen);

    // Set up Accelerate vImage buffers
    vImage_Buffer srcBuffer = {
        .data = bgraData,
        .height = fullHeight,
        .width = fullWidth,
        .rowBytes = bytesPerRow
    };
    vImage_Buffer destBuffer = {
        .data = rgbaData,
        .height = fullHeight,
        .width = fullWidth,
        .rowBytes = bytesPerRow
    };

    // Define the channel permutation to convert BGRA to RGBA
    uint8_t permuteMap[4] = {2, 1, 0, 3}; // Maps BGRA -> RGBA

    // Perform the channel permutation
    vImage_Error error = vImagePermuteChannels_ARGB8888(&srcBuffer, &destBuffer, permuteMap, kvImageNoFlags);
    if (error != kvImageNoError) {
        NSLog(@"vImage error: %ld", error);
    }

    free(bgraData);

    self.owner.frameCallback(self.owner.id, rgbaData, fullLen, (int)fullWidth, (int)fullHeight, (int)bytesPerRow);
}

@end


@interface CaptureController ()
@property (nonatomic, strong) SCStream *stream;
@property (nonatomic, strong) dispatch_queue_t captureQueue;
@property (nonatomic, strong) StreamOutput *streamOutput;
@end

@implementation CaptureController

- (instancetype)init {
    self = [super init];
    if (self) {
        // ...
    }
    return self;
}

- (void)startWindowCapture:(SCWindow *)scWin {
    CGRect windowRect = scWin.frame;

    NSLog(@"Window bounding rect: %@", NSStringFromRect(*(NSRect *)&windowRect));

    CGDirectDisplayID matchingDisplayID = [self displayForWindowRect:windowRect];
    if (matchingDisplayID == kCGNullDirectDisplay) {
        NSLog(@"Could not find a matching display for window: %@", scWin.title);
        return;
    }

    SCDisplay *matchingSCDisplay = [self scDisplayForCGDirectDisplayID:matchingDisplayID];
    if (!matchingSCDisplay) {
        NSLog(@"Could not convert CGDirectDisplayID %u to an SCDisplay.", matchingDisplayID);
        return;
    }

    SCContentFilter *filter =
      [[SCContentFilter alloc] initWithDisplay:matchingSCDisplay
                               includingWindows:@[ scWin ]];


    CGRect displayRect = matchingSCDisplay.frame;

    CGRect relativeRect = CGRectMake(
        windowRect.origin.x - displayRect.origin.x,
        windowRect.origin.y - displayRect.origin.y,
        windowRect.size.width,
        windowRect.size.height
    );

    SCStreamConfiguration *config = [SCStreamConfiguration new];
    config.queueDepth = 3;
    config.minimumFrameInterval = CMTimeMake(1, 30);
    config.width = matchingSCDisplay.width;
    config.height = matchingSCDisplay.height;
    config.pixelFormat = kCVPixelFormatType_32BGRA;

    // Create stream
    self.stream = [[SCStream alloc] initWithFilter:filter
                                     configuration:config
                                          delegate:nil];
    if (!self.stream) {
        NSLog(@"Error: Failed to create SCStream");
        return;
    }

    self.streamOutput = [[StreamOutput alloc] init];
    self.streamOutput.owner = self;

    self.captureQueue = dispatch_queue_create("com.revolutionmacro.captureQueue", DISPATCH_QUEUE_SERIAL);

    NSError *addError = nil;
    BOOL didAdd = [self.stream addStreamOutput:self.streamOutput
                                          type:SCStreamOutputTypeScreen
                            sampleHandlerQueue:self.captureQueue
                                         error:&addError];
    if (!didAdd) {
        NSLog(@"Error adding stream output: %@", addError);
        return;
    }

    // 5) Start capture
    [self.stream startCaptureWithCompletionHandler:^(NSError * _Nullable error) {
        if (error) {
            NSLog(@"startCapture error: %@", error);
        } else {
            NSLog(@"Capture started for windowID=%u", scWin.windowID);
        }
    }];
}


- (CGDirectDisplayID)displayForWindowRect:(CGRect)windowRect {
    uint32_t maxDisplays = 16;
    CGDirectDisplayID displayIDs[16];
    uint32_t displayCount = 0;
    CGGetActiveDisplayList(maxDisplays, displayIDs, &displayCount);

    CGDirectDisplayID bestDisplay = kCGNullDirectDisplay;
    CGFloat bestOverlap = 0;

    for (uint32_t i = 0; i < displayCount; i++) {
        CGDirectDisplayID dID = displayIDs[i];
        CGRect displayBounds = CGDisplayBounds(dID);

        CGRect intersection = CGRectIntersection(displayBounds, windowRect);
        CGFloat overlapArea = intersection.size.width * intersection.size.height;
        if (overlapArea > bestOverlap) {
            bestOverlap = overlapArea;
            bestDisplay = dID;
        }
    }

    return bestDisplay;
}

- (SCDisplay *)scDisplayForCGDirectDisplayID:(CGDirectDisplayID)displayID {
    __block SCDisplay *match = nil;
    dispatch_semaphore_t sem = dispatch_semaphore_create(0);

    [SCShareableContent getShareableContentWithCompletionHandler:^(SCShareableContent * _Nullable content, NSError * _Nullable error) {
        if (content) {
            for (SCDisplay *disp in content.displays) {
                if (disp.displayID == displayID) {
                    match = disp;
                    break;
                }
            }
        }
        dispatch_semaphore_signal(sem);
    }];

    dispatch_semaphore_wait(sem, DISPATCH_TIME_FOREVER);
    return match;
}

- (void)stopCapture {
    [self.stream stopCaptureWithCompletionHandler:^(NSError * _Nullable error) {
        if (error) {
            NSLog(@"stopCapture error: %@", error);
        } else {
            NSLog(@"Capture stopped.");
        }
    }];
}

@end
