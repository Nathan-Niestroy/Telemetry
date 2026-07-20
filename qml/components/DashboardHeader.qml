import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal

Rectangle {
    id: header

    required property url iconSource
    required property string signedInEmail
    required property bool administrator
    required property bool sendingReport
    required property bool budgetActive
    property color mutedText: "#91adbf"

    signal addAccountRequested()
    signal assetBreakdownRequested()
    signal manageFamilyRequested()
    signal sendBreakdownRequested()
    signal emailSettingsRequested()
    signal signOutRequested()

    height: 76
    color: "#08192c"
    border.color: "#102e49"

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 22
        anchors.verticalCenter: parent.verticalCenter
        spacing: 11

        Image {
            width: 42
            height: 42
            source: header.iconSource
            fillMode: Image.PreserveAspectFit
            mipmap: true
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            Label {
                text: "Telemetry"
                font.pixelSize: 21
                font.bold: true
                color: "#55dff4"
            }
            Label {
                text: "Family finances"
                font.pixelSize: 12
                color: header.mutedText
            }
        }
    }

    Row {
        anchors.right: parent.right
        anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8

        Label {
            anchors.verticalCenter: parent.verticalCenter
            text: header.signedInEmail + (header.administrator ? "  •  Admin" : "")
            color: header.mutedText
            visible: header.width >= 1080
        }
        ToolButton {
            id: moreButton
            text: "•••"
            font.pixelSize: 18
            Accessible.name: "More dashboard actions"
            onClicked: actionsMenu.open()

            Menu {
                id: actionsMenu
                y: moreButton.height

                MenuItem {
                    text: "Add account"
                    visible: header.administrator && !header.budgetActive
                    height: visible ? implicitHeight : 0
                    onTriggered: header.addAccountRequested()
                }
                MenuItem {
                    text: "Asset breakdown"
                    visible: !header.budgetActive
                    height: visible ? implicitHeight : 0
                    onTriggered: header.assetBreakdownRequested()
                }
                MenuSeparator {
                    visible: !header.budgetActive
                    height: visible ? implicitHeight : 0
                }
                MenuItem {
                    text: header.sendingReport ? "Sending breakdown…" : "Send breakdown"
                    visible: header.administrator
                    height: visible ? implicitHeight : 0
                    enabled: !header.sendingReport
                    onTriggered: header.sendBreakdownRequested()
                }
                MenuItem {
                    text: "Manage family"
                    visible: header.administrator
                    height: visible ? implicitHeight : 0
                    onTriggered: header.manageFamilyRequested()
                }
                MenuItem {
                    text: "Email report settings"
                    visible: header.administrator
                    height: visible ? implicitHeight : 0
                    onTriggered: header.emailSettingsRequested()
                }
                MenuSeparator {
                    visible: header.administrator
                    height: visible ? implicitHeight : 0
                }
                MenuItem {
                    text: "Sign out"
                    onTriggered: header.signOutRequested()
                }
            }
        }
    }
}
