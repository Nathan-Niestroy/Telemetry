import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Dialog {
    id: dialog
    title: "Manage users"
    modal: true
    anchors.centerIn: parent
    width: 500
    height: 560
    standardButtons: Dialog.Close

    // Remember the selected user while the confirmation dialog is open.
    property int pendingDeleteUserId: -1
    property string pendingDeleteUsername: ""

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
            placeholderText: "Username"
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

        // Only non-sensitive user metadata is provided by UserController.
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
                        width: parent.width - deleteButton.width - parent.spacing
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.username
                              + (modelData.is_admin ? " - Administrator" : "")
                              + (modelData.is_current ? " - Signed in" : "")
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
            text: "Factory reset Telemetry"
            onClicked: resetConfirmation.open()
        }
    }

    // Destructive actions always require a separate confirmation.
    Dialog {
        id: deleteConfirmation
        anchors.centerIn: parent
        modal: true
        title: "Delete user?"
        standardButtons: Dialog.Yes | Dialog.No

        Label {
            text: "Delete " + dialog.pendingDeleteUsername
                  + " and all of their financial accounts?"
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
