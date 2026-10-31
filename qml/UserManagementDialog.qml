import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    signal emailSettingsRequested()
    title: "Manage family"
    modal: true
    anchors.centerIn: parent
    width: 700
    height: 760
    standardButtons: Dialog.Close

    property int pendingDeleteUserId: -1
    property string pendingDeleteUsername: ""
    property int pendingEditUserId: -1

    Column {
        width: parent.width
        spacing: 12

        Label {
            text: "Create user"
            font.bold: true
            font.pixelSize: 18
        }

        TextField {
            id: newUsername
            width: parent.width
            placeholderText: "Email address"
            inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
        }

        TextField {
            id: newPassword
            width: parent.width
            placeholderText: "Temporary password (10+ characters)"
            echoMode: TextInput.Password
        }

        Button {
            width: parent.width
            text: "Create user"
            enabled: newUsername.text.length > 0 && newPassword.text.length > 0
            onClicked: {
                if (userController.createUser(newUsername.text, newPassword.text)) {
                    newUsername.clear()
                    newPassword.clear()
                }
            }
        }

        Label {
            width: parent.width
            text: userController.message
            color: "#ff8a8a"
            wrapMode: Text.WordWrap
            visible: text.length > 0
        }

        Label {
            text: "Local users"
            font.bold: true
            font.pixelSize: 18
        }

        ListView {
            width: parent.width
            height: 175
            spacing: 6
            clip: true
            model: userController.users

            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width
                height: 52
                radius: 6
                color: "#0c213a"

                Row {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 8

                    Label {
                        width: parent.width - editButton.width - deleteButton.width
                               - (parent.spacing * 2)
                        anchors.verticalCenter: parent.verticalCenter
                        elide: Text.ElideRight
                        text: modelData.username
                              + (modelData.is_admin ? " - Administrator" : "")
                              + (modelData.must_change_password ? " - Password change pending" : "")
                              + (modelData.is_current ? " - Signed in" : "")
                    }

                    Button {
                        id: editButton
                        text: "Edit"
                        onClicked: {
                            dialog.pendingEditUserId = modelData.id
                            editEmailField.text = modelData.username
                            editEmailDialog.open()
                        }
                    }

                    Button {
                        id: deleteButton
                        text: "Delete"
                        enabled: !modelData.is_current
                        onClicked: {
                            dialog.pendingDeleteUserId = modelData.id
                            dialog.pendingDeleteUsername = modelData.username
                            deleteConfirmation.open()
                        }
                    }
                }
            }
        }

        Button {
            width: parent.width
            text: "Email report settings"
            onClicked: dialog.emailSettingsRequested()
        }

        Label {
            text: "Backup and recovery"
            font.bold: true
            font.pixelSize: 18
        }

        Row {
            width: parent.width
            spacing: 8
            Button {
                width: (parent.width - parent.spacing) / 2
                text: "Create encrypted backup"
                onClicked: {
                    createBackupPassword.clear()
                    createBackupPasswordDialog.open()
                    createBackupPassword.forceActiveFocus()
                }
            }
            Button {
                width: (parent.width - parent.spacing) / 2
                text: "Restore backup"
                onClicked: restoreConfirmation.open()
            }
        }

        Label {
            width: parent.width
            text: backupController.message
            color: text.indexOf("success") >= 0 ? "#55e879" : "#ffcc66"
            wrapMode: Text.WordWrap
            visible: text.length > 0
        }

        Button {
            width: parent.width
            text: "Factory reset Telemetry"
            onClicked: resetConfirmation.open()
        }
    }

    Dialog {
        id: createBackupPasswordDialog
        anchors.centerIn: parent
        modal: true
        title: "Create backup password"
        standardButtons: Dialog.Ok | Dialog.Cancel

        Column {
            width: 380
            spacing: 10

            Label {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "Enter a password of at least 12 characters to encrypt this backup."
            }

            TextField {
                id: createBackupPassword
                width: parent.width
                placeholderText: "Backup password (12+ characters)"
                echoMode: TextInput.Password
                onAccepted: {
                    if (text.length >= 12)
                        createBackupPasswordDialog.accept()
                }
            }
        }

        onAccepted: {
            if (createBackupPassword.text.length < 12) {
                open()
                createBackupPassword.forceActiveFocus()
                return
            }
            backupController.createBackup(createBackupPassword.text)
            createBackupPassword.clear()
        }
        onRejected: createBackupPassword.clear()
    }

    Dialog {
        id: restoreConfirmation
        anchors.centerIn: parent
        modal: true
        title: "Restore backup?"
        standardButtons: Dialog.Yes | Dialog.No
        Label {
            width: 380
            wrapMode: Text.WordWrap
            text: "This replaces all current Telemetry data after validating the encrypted backup. Telemetry will close after restore."
        }
        onAccepted: {
            restorePassword.clear()
            restorePasswordDialog.open()
            restorePassword.forceActiveFocus()
        }
    }

    Dialog {
        id: restorePasswordDialog
        anchors.centerIn: parent
        modal: true
        title: "Enter backup password"
        standardButtons: Dialog.Ok | Dialog.Cancel

        Column {
            width: 380
            spacing: 10

            Label {
                width: parent.width
                wrapMode: Text.WordWrap
                text: "Enter the password used when this encrypted backup was created."
            }

            TextField {
                id: restorePassword
                width: parent.width
                placeholderText: "Backup password"
                echoMode: TextInput.Password
                onAccepted: {
                    if (text.length > 0)
                        restorePasswordDialog.accept()
                }
            }
        }

        onAccepted: {
            if (restorePassword.text.length === 0) {
                open()
                restorePassword.forceActiveFocus()
                return
            }
            backupController.restoreBackup(restorePassword.text)
            restorePassword.clear()
        }
        onRejected: restorePassword.clear()
    }

    Dialog {
        id: editEmailDialog
        anchors.centerIn: parent
        modal: true
        title: "Update login email"
        standardButtons: Dialog.Save | Dialog.Cancel

        TextField {
            id: editEmailField
            width: 360
            placeholderText: "Email address"
            inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
        }

        onAccepted: {
            if (!userController.updateUserEmail(dialog.pendingEditUserId,
                                                editEmailField.text))
                open()
        }
    }

    Dialog {
        id: deleteConfirmation
        anchors.centerIn: parent
        modal: true
        title: "Delete user?"
        standardButtons: Dialog.Yes | Dialog.No

        Label {
            width: 380
            wrapMode: Text.WordWrap
            text: "Delete the login for " + dialog.pendingDeleteUsername
                  + "? Shared family financial data will be kept."
        }

        onAccepted: userController.deleteUser(dialog.pendingDeleteUserId)
    }

    Dialog {
        id: resetConfirmation
        anchors.centerIn: parent
        modal: true
        title: "Factory reset Telemetry?"
        standardButtons: Dialog.Yes | Dialog.No

        Label {
            width: 360
            wrapMode: Text.WordWrap
            text: "This permanently deletes every local user and financial account. "
                  + "Telemetry will return to the first-launch registration screen."
        }

        onAccepted: {
            if (userController.factoryReset()) {
                dialog.close()
            }
        }
    }
}
