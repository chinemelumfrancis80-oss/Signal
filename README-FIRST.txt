SIGNAL ANDROID APP

This project wraps the deployed Signal website:
https://signal-ndef.onrender.com

To build the APK using GitHub:
1. Upload all files/folders in this project to the Signal repository.
2. Commit to the main/master branch.
3. Open GitHub > your Signal repository > Actions.
4. Open "Build Signal APK".
5. Wait for the workflow to finish successfully.
6. Open the completed workflow run and download the "Signal-debug-apk" artifact.
7. Extract the ZIP and install app-debug.apk on Android.

The APK is a WebView app, so the phone needs internet access to load the deployed Signal site.
