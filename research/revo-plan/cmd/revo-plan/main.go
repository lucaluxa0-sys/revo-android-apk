package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"

	"revo-clone-core/planner"
)

func main() {
	path := flag.String("script", "", "Recovered Revolution Lua pattern to statically compile")
	width := flag.Float64("width", 2, "Pattern width in game studs")
	length := flag.Float64("length", 8, "Pattern length in game studs")
	iteration := flag.Float64("iteration", 1, "Pattern iteration")
	msPerStud := flag.Float64("ms-per-stud", 62.5, "Provisional Android timing calibration")
	out := flag.String("out", "", "JSON output file (default stdout)")
	flag.Parse()
	if *path == "" {
		fmt.Fprintln(os.Stderr, "missing -script file")
		os.Exit(2)
	}
	raw, err := os.ReadFile(*path)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	p, err := planner.Compile(string(raw), planner.Options{
		Width: *width, Length: *length, Iteration: *iteration,
		MsPerStud: *msPerStud, MaxActions: 512, Timeout: 3 * time.Second,
	})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	result, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	result = append(result, '\n')
	if *out == "" {
		_, err = os.Stdout.Write(result)
	} else {
		err = os.WriteFile(*out, result, 0644)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
