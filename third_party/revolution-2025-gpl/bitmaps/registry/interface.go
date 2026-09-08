package registry

type Registry interface {
	RegisterPng(name string, data []byte)
	RegisterBase64(name string, data string)
}
