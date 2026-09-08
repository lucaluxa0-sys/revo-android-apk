package vichop

import (
	"fmt"
	"github.com/nosyliam/revolution/opencv"
	"github.com/nosyliam/revolution/pkg/config"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"io"
	"net/http"
	"os"
)

type Descriptor struct {
	Rows int    `bson:"rows"`
	Cols int    `bson:"cols"`
	Type int    `bson:"type"`
	Data []byte `bson:"data"`
}

type Parameters struct {
	Gamma             float64 `bson:"gamma"`
	LoweRatio         float64 `bson:"lowe_ratio"`
	MinClusterDensity int     `bson:"min_cluster_density"`
	Epsilon           float64 `bson:"epsilon"`
	KeypointRadius    float64 `bson:"keypoint_radius"`
	MatchThreshold    int     `bson:"match_threshold"`
	CutBottom         int     `bson:"cut_bottom"`
	CutTop            int     `bson:"cut_top"`
	CutLeft           int     `bson:"cut_left"`
	CutRight          int     `bson:"cut_right"`
	FileOutput        bool    `bson:"-"`

	// SIFT Parameters
	OctaveLayers      int     `bson:"octave_layers"`
	ContrastThreshold float64 `bson:"contrast_threshold"`
	EdgeThreshold     float64 `bson:"edge_threshold"`
	Sigma             float64 `bson:"sigma"`

	Mat opencv.Mat
}

type Field struct {
	Parameters

	Descriptor Descriptor `bson:"descriptor"`
}

type DescriptorFile struct {
	Version string `bson:"version"`

	Fields map[string]*Field `bson:"fields"`
}

type Dataset struct {
	version string
	state   *config.Object[config.State]

	Descriptor *DescriptorFile
}

func NewDataset(state *config.Object[config.State]) *Dataset {
	return &Dataset{state: state}
}

func (d *Dataset) CheckVersion() error {
	resp, err := http.Get("https://raw.githubusercontent.com/nosyliam/revolution/refs/heads/main/pkg/vichop/dataset/version")
	if err != nil {
		return errors.Wrap(err, "failed to download dataset version")
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return errors.Wrap(err, "failed to read dataset version")
	}

	d.version = string(data)
	return nil
}

func (d *Dataset) Update() error {
	d.state.SetPath("vicHop.downloadingDataset", true)
	defer d.state.SetPath("vicHop.downloadingDataset", false)
	resp, err := http.Get("https://raw.githubusercontent.com/nosyliam/revolution/refs/heads/main/pkg/vichop/dataset/vichop.bin")
	if err != nil {
		return errors.Wrap(err, "failed to download dataset")
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return errors.Errorf("Failed to download dataset: HTTP status %s", resp.Status)
	}

	file, err := os.Create("vichop.bin")
	if err != nil {
		return errors.Wrap(err, "failed to create dataset file")
	}
	defer file.Close()

	_, err = io.Copy(file, resp.Body)
	if err != nil {
		return errors.Wrap(err, "failed to write to dataset file")
	}

	return d.Load()
}

func (d *Dataset) Load() error {
	if _, err := os.Stat("vichop.bin"); os.IsNotExist(err) {
		return nil
	}

	fileData, err := os.ReadFile("vichop.bin")
	if err != nil {
		d.state.SetPath("vicHop.datasetVersion", "INVALID")
		return errors.Wrap(err, "failed to read dataset file")
	}

	d.Descriptor = &DescriptorFile{}
	err = bson.Unmarshal(fileData, d.Descriptor)
	if err != nil {
		d.Descriptor = nil
		d.state.SetPath("vicHop.datasetVersion", "INVALID")
		return errors.Wrap(err, "failed to unmarshal dataset file")
	}

	d.state.SetPath("vicHop.datasetVersion", d.Descriptor.Version)
	if d.Descriptor.Version == d.version {
		d.state.SetPath("vicHop.upToDate", true)
	}

	for name, field := range d.Descriptor.Fields {
		mat, err := opencv.NewMatFromBytes(field.Descriptor.Rows, field.Descriptor.Cols, opencv.MatType(field.Descriptor.Type), field.Descriptor.Data)
		if err != nil {
			return errors.Wrap(err, fmt.Sprintf("failed to map descriptor for field %s", name))
		}
		field.Mat = mat
	}

	return nil
}
