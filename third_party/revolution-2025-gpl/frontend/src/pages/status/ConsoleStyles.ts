export default {
    container: {
        minHeight: '100%',
        maxWidth: '100%',
        borderRadius: '5px',
        overflow: 'auto',
        cursor: 'text',
        backgroundColor: '#ededed',
        backgroundSize: 'cover',
        flexGrow: 1
    },
    content: {
        padding: '15px',
        height: '100%',
        fontSize: '12px',
        color: '#000000',
        fontFamily: 'monospace'
    },
    inputArea: {
        display: 'inline-flex',
        width: '100%'
    },
    promptLabel: {
        color: '#a5a5a5',
    },
    inputText: {
        fontSize: '12px',
        color: '#a5a5a5',
        fontFamily: 'monospace',
        paddingTop: '3px'
    },
    input: {
        border: '0',
        padding: '0 0 0 7px',
        margin: '0',
        flexGrow: '100',
        width: '100%',
        height: '22px',
        background: 'transparent',
        outline: 'none' // Fix for outline showing up on some browsers
    }
}