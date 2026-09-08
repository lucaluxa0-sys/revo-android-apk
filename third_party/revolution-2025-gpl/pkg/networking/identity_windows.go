//go:build windows
// +build windows

package networking

import (
	"github.com/sqweek/dialog"
	"os"
	"os/user"
	"strings"
	"syscall"
)

var ComputerName string
var UserName string

func getIdentity() string {
	return strings.Replace(ComputerName+"/"+UserName, "\\", "/", -1)
}

func getComputerName() (string, error) {
	var size uint32 = 256
	buf := make([]uint16, size)
	err := syscall.GetComputerName(&buf[0], &size)
	if err != nil {
		return "", err
	}
	return syscall.UTF16ToString(buf[:size]), nil
}

func getUserName() (string, error) {
	u, err := user.Current()
	if err != nil {
		return "", err
	}
	return u.Username, nil
}

func init() {
	var err error
	ComputerName, err = getComputerName()
	if err != nil {
		dialog.Message("Failed to get computer name: %s", err.Error()).Error()
		os.Exit(1)
	}
	UserName, err = getUserName()
	if err != nil {
		dialog.Message("Failed to get user name: %s", err.Error()).Error()
		os.Exit(1)
	}
}
