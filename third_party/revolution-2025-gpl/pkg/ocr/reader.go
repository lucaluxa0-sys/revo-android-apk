package ocr

import (
	"bufio"
	_ "embed"
	"encoding/binary"
	"fmt"
	"github.com/pkg/errors"
	"image"
	"os"
	"os/exec"
	"path"
	"runtime"
)

type Result struct {
	Text  string
	Error *string
}

type Scan struct {
	image  *image.RGBA
	out    chan Result
	finish chan bool
}

type Reader struct {
	queue  chan *Scan
	err    chan<- string
	ready  chan bool
	closed bool
	cmd    *exec.Cmd
}

func (r *Reader) Start() {
	inPipe, err := r.cmd.StdinPipe()
	if err != nil {
		r.err <- errors.Wrap(err, "failed to get pipe to OCR subprocess input").Error()
		return
	}

	outPipe, err := r.cmd.StdoutPipe()
	if err != nil {
		r.err <- errors.Wrap(err, "failed to get pipe to OCR subprocess output").Error()
		return
	}

	if err := r.cmd.Start(); err != nil {
		r.err <- errors.Wrap(err, "Failed to start OCR subprocess").Error()
		return
	}

	var activeScan *Scan
	var ready bool

	go func() {
		<-r.ready
		ready = true
		for !r.closed {
			scan := <-r.queue
			activeScan = scan
			length := make([]byte, 4)
			binary.LittleEndian.PutUint32(length, uint32(len(scan.image.Pix)))
			if _, err := inPipe.Write(length); err != nil {
				r.err <- errors.Wrap(err, "Failed to write data to OCR subprocess").Error()
				break
			}
			bounds := scan.image.Bounds()
			width := make([]byte, 4)
			binary.LittleEndian.PutUint32(width, uint32(bounds.Dx()))
			if _, err := inPipe.Write(width); err != nil {
				r.err <- errors.Wrap(err, "Failed to write data to OCR subprocess").Error()
				break
			}
			height := make([]byte, 4)
			binary.LittleEndian.PutUint32(height, uint32(bounds.Dy()))
			if _, err := inPipe.Write(height); err != nil {
				r.err <- errors.Wrap(err, "Failed to write data to OCR subprocess").Error()
				break
			}
			if _, err := inPipe.Write(scan.image.Pix); err != nil {
				r.err <- errors.Wrap(err, "Failed to write data to OCR subprocess").Error()
				break
			}

			<-scan.finish
		}
	}()

	go func() {
		scanner := bufio.NewScanner(outPipe)
		for scanner.Scan() {
			text := scanner.Text()
			if text[0] == 'R' {
				r.ready <- true
				continue
			} else if !ready {
				r.err <- "OCR subprocess returned unknown data while initializing"
				break
			}
			if activeScan == nil {
				r.err <- "OCR subprocess returned unexpected data"
			}
			fmt.Println("res", text)
			if len(text) > 3 && text[0:2] == "E=" {
				err := text[2:]
				activeScan.out <- Result{Error: &err}
				activeScan.finish <- true
				activeScan = nil
				continue
			}
			activeScan.finish <- true
			activeScan.out <- Result{Text: text}
			activeScan = nil
		}
	}()

	if err := r.cmd.Wait(); err != nil {
		r.err <- errors.Wrap(err, "OCR subprocess failed").Error()
	}
}

func (r *Reader) ReadImage(image *image.RGBA) <-chan Result {
	out := make(chan Result, 1)
	r.queue <- &Scan{image, out, make(chan bool, 1)}
	return out
}

func (r *Reader) Close() error {
	r.closed = true
	return r.cmd.Process.Kill()
}

func NewReader(errCh chan<- string) (*Reader, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return nil, errors.Wrap(err, "failed to get working directory")
	}
	bin := path.Join(cwd, fmt.Sprintf("ocrs_%s", runtime.GOOS))
	if _, err := os.Stat(bin); errors.Is(err, os.ErrNotExist) {
		// TODO: download binary
	}

	cmd := exec.Command(bin)

	return &Reader{cmd: cmd, err: errCh, ready: make(chan bool, 1), queue: make(chan *Scan, 100)}, nil
}
