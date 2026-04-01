const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
    const win = new BrowserWindow({
        width: 1200,
        height: 800,
        autoHideMenuBar: true, // Ẩn thanh menu (File, Edit, View...) cho giống app xịn
        webPreferences: {
            nodeIntegration: true
        }
    });

    // Load file index.html của bạn
    win.loadFile('index.html');
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});