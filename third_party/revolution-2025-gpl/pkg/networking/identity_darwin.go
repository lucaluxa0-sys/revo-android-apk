//go:build darwin
// +build darwin

package networking

import (
	"github.com/sqweek/dialog"
	"os"
	"os/exec"
	"os/user"
	"strings"
)

var ComputerName string
var UserName string

func getIdentity() string {
	return ComputerName + "/" + UserName
}

func getMacComputerName() (string, error) {
	out, err := exec.Command("scutil", "--get", "ComputerName").Output()
	if err != nil || len(out) == 0 {
		return os.Hostname()
	}
	return strings.TrimSpace(string(out)), nil
}

func getMacUserName() (string, error) {
	user, err := user.Current()
	if err != nil {
		return "", err
	}
	return user.Username, nil
}

func init() {
	var err error
	ComputerName, err = getMacComputerName()
	if err != nil {
		dialog.Message("Failed to get computer name: %s", err.Error()).Error()
		os.Exit(1)
	}
	UserName, err = getMacUserName()
	if err != nil {
		dialog.Message("Failed to get user name: %s", err.Error()).Error()
		os.Exit(1)
	}
}
