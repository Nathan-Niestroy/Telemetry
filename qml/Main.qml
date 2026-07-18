import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

// The main Telemetry window.
ApplicationWindow {
    visible: true
    width: 900
    height: 600
    title: "Telemetry"
    color: "#061326"

    Universal.theme: Universal.Dark
    Universal.accent: "#55e879"
    Universal.foreground: "#e8f7ff"
    Universal.background: "#061326"

    // Reusable modal forms remain outside the main content layout.
    AddAccountDialog {
        id: addAccountDialog

        onSaveRequested: {
            if (accountController.addAccount(
                    accountName, owner, accountType, balance)) {
                clearFields()
            } else {
                open()
            }
        }
    }

    UserManagementDialog {
        id: userManagementDialog
    }

    // Center the registration, login, or signed-in content.
    Column {
        anchors.centerIn: parent
        spacing: 16
        width: authController.loggedIn ? 560 : 340

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 128
            height: 128
            source: telemetryIconUrl
            fillMode: Image.PreserveAspectFit
            mipmap: true
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Telemetry"
            font.pixelSize: 30
            font.bold: true
            color: "#55dff4"
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: authController.hasUser ? "Sign in" : "Create your account"
            color: "#a9c4d6"
            font.pixelSize: 18
            visible: !authController.loggedIn
        }

        // Authentication fields are hidden as soon as a session begins.
        TextField {
            id: usernameField
            width: parent.width
            placeholderText: "Username"
            visible: !authController.loggedIn
        }

        TextField {
            id: passwordField
            width: parent.width
            placeholderText: "Password"
            echoMode: TextInput.Password
            visible: !authController.loggedIn
            onAccepted: submitButton.clicked()
        }

        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: authController.message
            color: "#ff8a8a"
            visible: !authController.loggedIn && text.length > 0
        }

        // Register on first launch and sign in on later launches.
        Button {
            id: submitButton
            width: parent.width
            text: authController.hasUser ? "Sign in" : "Create account"
            visible: !authController.loggedIn
            enabled: usernameField.text.length > 0 && passwordField.text.length > 0

            onClicked: {
                if (authController.hasUser) {
                    authController.login(usernameField.text, passwordField.text)
                } else {
                    authController.register(usernameField.text, passwordField.text)
                }
                passwordField.text = ""
            }
        }

        // Content below this point is only visible after login.
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Welcome, " + authController.username
            font.pixelSize: 20
            visible: authController.loggedIn
        }

        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "No financial accounts added yet."
            color: "#a9c4d6"
            visible: authController.loggedIn && accountController.accounts.length === 0
        }

        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            text: accountController.message
            color: "#ff8a8a"
            visible: authController.loggedIn && text.length > 0
        }

        ListView {
            width: parent.width
            height: Math.min(contentHeight, 260)
            spacing: 8
            clip: true
            model: accountController.accounts
            visible: authController.loggedIn && count > 0

            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 70
                radius: 8
                color: "#0c213a"
                border.color: "#17466a"

                Row {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 12

                    Column {
                        width: parent.width - balanceLabel.width - parent.spacing

                        Label {
                            text: modelData.name
                            font.bold: true
                            font.pixelSize: 17
                        }

                        Label {
                            text: modelData.owner + " - " + modelData.account_type
                            color: "#a9c4d6"
                        }
                    }

                    Label {
                        id: balanceLabel
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.balance
                        font.bold: true
                        color: "#55e879"
                    }
                }
            }
        }

        // Signed-in actions are kept below the account list.
        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Add account"
            visible: authController.loggedIn
            onClicked: addAccountDialog.open()
        }

        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Manage users"
            visible: authController.loggedIn && authController.isAdmin
            onClicked: userManagementDialog.open()
        }

        Button {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Sign out"
            visible: authController.loggedIn
            onClicked: authController.logout()
        }
    }
}
