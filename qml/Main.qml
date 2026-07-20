import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Universal
import "components"
import "dashboards"

ApplicationWindow {
    id: window
    visible: true
    width: 1080
    height: 760
    minimumWidth: 760
    minimumHeight: 620
    title: "Telemetry"
    color: "#061326"

    Universal.theme: Universal.Dark
    Universal.accent: "#147a96"
    Universal.foreground: "#e8f7ff"
    Universal.background: "#061326"

    property color panelColor: "#0a1d33"
    property color panelBorder: "#17466a"
    property color mutedText: "#91adbf"
    property color assetColor: "#55e879"
    property color debtColor: "#ff647c"
    property bool budgetPageActive: false
    property int pendingDeleteAccountId: -1
    property string pendingDeleteAccountName: ""

    AddAccountDialog {
        id: addAccountDialog
        onSaveRequested: {
            if (accountController.addAccount(accountName, owner, accountType, balance))
                clearFields()
            else
                open()
        }
    }

    EditAccountDialog {
        id: editAccountDialog
        onSaveRequested: function(accountId, accountName, owner, accountType, balance) {
            if (!accountController.updateAccount(accountId, accountName, owner,
                                                  accountType, balance))
                open()
        }
    }

    Dialog {
        id: deleteAccountConfirmation
        anchors.centerIn: parent
        modal: true
        title: "Remove family account?"
        standardButtons: Dialog.Yes | Dialog.No

        Label {
            width: 380
            wrapMode: Text.WordWrap
            text: "Permanently remove " + window.pendingDeleteAccountName
                  + " and all of its holdings? This cannot be undone."
        }

        onAccepted: accountController.deleteAccount(window.pendingDeleteAccountId)
    }

    UserManagementDialog {
        id: userManagementDialog
        onEmailSettingsRequested: emailSettingsDialog.open()
    }
    AssetBreakdownDialog { id: assetBreakdownDialog }
    EmailSettingsDialog { id: emailSettingsDialog }
    EmailPreviewDialog { id: emailPreviewDialog }
    Connections {
        target: authController

        function onUser_logged_out() {
            usernameField.clear()
            passwordField.clear()
            window.budgetPageActive = false
        }
    }

    Column {
        anchors.centerIn: parent
        width: 360
        spacing: 15
        visible: !authController.loggedIn

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 112
            height: 112
            source: telemetryIconUrl
            fillMode: Image.PreserveAspectFit
            mipmap: true
        }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Telemetry"
            font.pixelSize: 31
            font.bold: true
            color: "#55dff4"
        }
        Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: authController.hasUser ? "Welcome back" : "Create your family account"
            color: window.mutedText
            font.pixelSize: 17
        }
        TextField {
            id: usernameField
            width: parent.width
            placeholderText: "Email address"
            inputMethodHints: Qt.ImhEmailCharactersOnly | Qt.ImhNoAutoUppercase
        }
        TextField {
            id: passwordField
            width: parent.width
            placeholderText: "Password"
            echoMode: TextInput.Password
            onAccepted: submitButton.clicked()
        }
        Label {
            width: parent.width
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            text: authController.message
            color: window.debtColor
            visible: text.length > 0
        }
        Button {
            id: submitButton
            width: parent.width
            text: authController.hasUser ? "Sign in" : "Create account"
            enabled: usernameField.text.length > 0 && passwordField.text.length > 0
            highlighted: true
            onClicked: {
                if (authController.hasUser)
                    authController.login(usernameField.text, passwordField.text)
                else
                    authController.register(usernameField.text, passwordField.text)
                passwordField.text = ""
            }
        }
    }

    Column {
        anchors.centerIn: parent
        width: 390
        spacing: 15
        visible: authController.loggedIn && authController.mustChangePassword

        Label {
            width: parent.width
            text: "Create your new password"
            horizontalAlignment: Text.AlignHCenter
            font.pixelSize: 27
            font.bold: true
            color: "#55dff4"
        }
        Label {
            width: parent.width
            text: "Your administrator gave you a temporary password. Choose a different password before continuing."
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: window.mutedText
        }
        TextField {
            id: requiredPasswordField
            width: parent.width
            placeholderText: "New password (10+ characters)"
            echoMode: TextInput.Password
        }
        TextField {
            id: requiredPasswordConfirmation
            width: parent.width
            placeholderText: "Confirm new password"
            echoMode: TextInput.Password
            onAccepted: changePasswordButton.clicked()
        }
        Label {
            width: parent.width
            text: authController.message
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
            color: window.debtColor
            visible: text.length > 0
        }
        Button {
            id: changePasswordButton
            width: parent.width
            text: "Save password and continue"
            highlighted: true
            enabled: requiredPasswordField.text.length > 0
                     && requiredPasswordConfirmation.text.length > 0
            onClicked: {
                if (authController.changeRequiredPassword(
                            requiredPasswordField.text,
                            requiredPasswordConfirmation.text)) {
                    requiredPasswordField.clear()
                    requiredPasswordConfirmation.clear()
                }
            }
        }
        Button {
            width: parent.width
            text: "Sign out"
            onClicked: {
                requiredPasswordField.clear()
                requiredPasswordConfirmation.clear()
                authController.logout()
            }
        }
    }

    Item {
        anchors.fill: parent
        visible: authController.loggedIn && !authController.mustChangePassword

        DashboardHeader {
            id: header
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            iconSource: telemetryIconUrl
            signedInEmail: authController.username
            administrator: authController.isAdmin
            sendingReport: reportController.sending
            budgetActive: window.budgetPageActive
            mutedText: window.mutedText
            onAddAccountRequested: addAccountDialog.open()
            onAssetBreakdownRequested: assetBreakdownDialog.openOverview()
            onManageFamilyRequested: userManagementDialog.open()
            onSendBreakdownRequested: {
                if (!reportController.configured)
                    emailSettingsDialog.open()
                else if (reportController.preparePreview())
                    emailPreviewDialog.open()
            }
            onEmailSettingsRequested: emailSettingsDialog.open()
            onSignOutRequested: authController.logout()
        }

        Rectangle {
            id: dashboardNavigation
            anchors.top: header.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 52
            color: "#07172a"
            border.color: window.panelBorder

            Rectangle {
                anchors.centerIn: parent
                width: 270
                height: 38
                radius: 9
                color: window.panelColor
                border.color: window.panelBorder

                Row {
                    anchors.fill: parent
                    anchors.margins: 3
                    spacing: 3

                    Button {
                        width: (parent.width - parent.spacing) / 2
                        height: parent.height
                        text: "Net worth"
                        flat: true
                        highlighted: !window.budgetPageActive
                        onClicked: window.budgetPageActive = false
                    }
                    Button {
                        width: (parent.width - parent.spacing) / 2
                        height: parent.height
                        text: "Budget"
                        flat: true
                        highlighted: window.budgetPageActive
                        onClicked: window.budgetPageActive = true
                    }
                }
            }
        }

        ScrollView {
            anchors.top: dashboardNavigation.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            contentWidth: availableWidth
            clip: true
            opacity: window.budgetPageActive ? 0 : 1
            visible: opacity > 0
            enabled: !window.budgetPageActive
            Behavior on opacity { NumberAnimation { duration: 160 } }

            Column {
                width: Math.min(parent.width, 1280)
                anchors.horizontalCenter: parent.horizontalCenter
                padding: 24
                spacing: 20

                Column {
                    width: parent.width - 48
                    spacing: 4
                    Label {
                        text: "Family net worth"
                        font.pixelSize: 27
                        font.bold: true
                        color: "#f4fbff"
                    }
                    Label {
                        text: "A current view of everything your family owns and owes."
                        font.pixelSize: 14
                        color: window.mutedText
                    }
                }

                Row {
                    width: parent.width - 48
                    spacing: 14

                    Repeater {
                        model: [
                            { label: "NET WORTH", value: accountController.totalNetWorth, color: "#f4fbff" },
                            { label: "TOTAL ASSETS", value: accountController.totalAssets, color: window.assetColor },
                            { label: "TOTAL DEBT", value: accountController.totalDebt, color: window.debtColor }
                        ]
                        delegate: Rectangle {
                            required property var modelData
                            width: (parent.width - 28) / 3
                            height: 110
                            radius: 14
                            color: window.panelColor
                            border.color: window.panelBorder
                            Rectangle {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.bottom: parent.bottom
                                anchors.margins: 10
                                width: 4
                                radius: 2
                                color: modelData.color
                            }
                            Column {
                                anchors.left: parent.left; anchors.leftMargin: 24
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 8
                                Label { text: modelData.label; color: window.mutedText; font.pixelSize: 11; font.bold: true; font.letterSpacing: 1.2 }
                                Label { text: modelData.value; color: modelData.color; font.pixelSize: 27; font.bold: true }
                            }
                        }
                    }
                }

                Label {
                    width: parent.width - 48
                    text: reportController.message
                    color: reportController.message.indexOf("successfully") >= 0
                           ? window.assetColor : window.debtColor
                    wrapMode: Text.WordWrap
                    visible: authController.isAdmin && text.length > 0
                }

                Rectangle {
                    width: parent.width - 48
                    height: 270
                    radius: 14
                    color: window.panelColor
                    border.color: window.panelBorder

                    Row {
                        anchors.fill: parent
                        anchors.margins: 26
                        spacing: 30

                        Canvas {
                            id: compositionChart
                            width: 200; height: 200
                            property var colors: ["#55e879", "#55dff4", "#a78bfa", "#f6c453", "#6ea8fe"]
                            property int hoveredIndex: -1
                            property real grossTotal: {
                                var total = 0
                                for (var i = 0; i < accountController.accounts.length; ++i)
                                    total += accountController.accounts[i].balance_cents
                                return total
                            }
                            property var hoveredAccount: hoveredIndex >= 0
                                                         && hoveredIndex < accountController.accounts.length
                                                         ? accountController.accounts[hoveredIndex] : null

                            function setHoveredIndex(index) {
                                if (hoveredIndex !== index) {
                                    hoveredIndex = index
                                    requestPaint()
                                }
                            }

                            function selectSlice(x, y) {
                                var dx = x - width / 2
                                var dy = y - height / 2
                                var distance = Math.sqrt(dx * dx + dy * dy)
                                if (distance < 66 || distance > 99 || grossTotal <= 0) {
                                    setHoveredIndex(-1)
                                    return
                                }
                                var angle = Math.atan2(dy, dx) + Math.PI / 2
                                if (angle < 0)
                                    angle += Math.PI * 2
                                var running = 0
                                for (var i = 0; i < accountController.accounts.length; ++i) {
                                    running += Math.PI * 2
                                               * accountController.accounts[i].balance_cents
                                               / grossTotal
                                    if (angle <= running) {
                                        setHoveredIndex(i)
                                        return
                                    }
                                }
                                setHoveredIndex(-1)
                            }

                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.reset()
                                var accounts = accountController.accounts
                                var total = 0
                                for (var i = 0; i < accounts.length; ++i)
                                    total += accounts[i].balance_cents
                                var cx = width / 2, cy = height / 2, radius = 82
                                if (total <= 0) {
                                    ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2)
                                    ctx.lineWidth = 25; ctx.strokeStyle = "#17314d"; ctx.stroke()
                                    return
                                }
                                var angle = -Math.PI / 2
                                for (i = 0; i < accounts.length; ++i) {
                                    var next = angle + Math.PI * 2 * accounts[i].balance_cents / total
                                    ctx.beginPath(); ctx.arc(cx, cy, radius, angle, next)
                                    ctx.lineWidth = i === hoveredIndex ? 32 : 25
                                    ctx.strokeStyle = accounts[i].is_debt ? window.debtColor
                                                                          : colors[i % colors.length]
                                    ctx.stroke(); angle = next
                                }
                            }
                            Connections {
                                target: accountController
                                function onAccounts_changed() { compositionChart.requestPaint() }
                            }
                            MouseArea {
                                id: chartMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                                onPositionChanged: function(mouse) {
                                    compositionChart.selectSlice(mouse.x, mouse.y)
                                }
                                onExited: compositionChart.setHoveredIndex(-1)

                                ToolTip.visible: containsMouse && compositionChart.hoveredAccount !== null
                                ToolTip.delay: 80
                                ToolTip.timeout: 10000
                                ToolTip.text: compositionChart.hoveredAccount === null ? "" :
                                              compositionChart.hoveredAccount.name + "\n"
                                              + (compositionChart.hoveredAccount.is_debt ? "Debt" : "Asset")
                                              + "  •  " + compositionChart.hoveredAccount.balance + "\n"
                                              + (compositionChart.grossTotal > 0
                                                 ? (compositionChart.hoveredAccount.balance_cents
                                                    * 100 / compositionChart.grossTotal).toFixed(1)
                                                   + "% of accounts"
                                                 : "")
                            }
                            Column {
                                anchors.centerIn: parent
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: compositionChart.hoveredAccount
                                          ? compositionChart.hoveredAccount.balance
                                          : accountController.accounts.length
                                    color: compositionChart.hoveredAccount
                                           ? (compositionChart.hoveredAccount.is_debt
                                              ? window.debtColor : window.assetColor)
                                           : "#e8f7ff"
                                    font.pixelSize: compositionChart.hoveredAccount ? 17 : 27
                                    font.bold: true
                                }
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: compositionChart.hoveredAccount
                                          ? (compositionChart.hoveredAccount.is_debt ? "debt" : "asset")
                                          : "accounts"
                                    color: window.mutedText
                                    font.pixelSize: 12
                                }
                            }
                        }

                        Column {
                            width: parent.width - compositionChart.width - parent.spacing
                            spacing: 10
                            Label { text: "Account composition"; color: "#f4fbff"; font.bold: true; font.pixelSize: 18 }
                            Label {
                                text: "See what makes up your family's assets and debt."
                                color: window.mutedText
                            }
                            Flow {
                                width: parent.width
                                spacing: 10
                                Repeater {
                                    model: accountController.accounts
                                    delegate: Rectangle {
                                        id: legendChip
                                        required property var modelData
                                        required property int index
                                        width: legendText.width + 28
                                        height: 30
                                        radius: 15
                                        color: compositionChart.hoveredIndex === index
                                               ? "#1a3b59" : "#102943"
                                        border.width: compositionChart.hoveredIndex === index ? 1 : 0
                                        border.color: modelData.is_debt ? window.debtColor
                                                                        : compositionChart.colors[index % compositionChart.colors.length]
                                        Row {
                                            anchors.centerIn: parent; spacing: 6
                                            Rectangle { width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter; color: modelData.is_debt ? window.debtColor : compositionChart.colors[index % compositionChart.colors.length] }
                                            Label { id: legendText; text: modelData.name; color: "#c5dbe8"; font.pixelSize: 11 }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onEntered: compositionChart.setHoveredIndex(legendChip.index)
                                            onExited: compositionChart.setHoveredIndex(-1)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                Rectangle {
                    width: parent.width - 48
                    height: Math.max(245, accountList.contentHeight + 104)
                    radius: 14
                    color: window.panelColor
                    border.color: window.panelBorder

                    Label {
                        id: accountHeading
                        anchors.left: parent.left; anchors.top: parent.top
                        anchors.margins: 18
                        text: "Family accounts"
                        color: "#f4fbff"; font.bold: true; font.pixelSize: 18
                    }
                    Label {
                        anchors.right: parent.right; anchors.verticalCenter: accountHeading.verticalCenter
                        anchors.rightMargin: 18
                        text: accountController.accounts.length + " total"
                        color: window.mutedText
                    }
                    Rectangle {
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: accountHeading.bottom; anchors.topMargin: 16
                        height: 1; color: window.panelBorder
                    }
                    Label {
                        anchors.centerIn: parent
                        text: authController.isAdmin ? "Add the first family account to get started." : "No family accounts have been added yet."
                        color: window.mutedText
                        visible: accountController.accounts.length === 0
                    }
                    ListView {
                        id: accountList
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.top: accountHeading.bottom; anchors.topMargin: 28
                        anchors.bottom: parent.bottom; anchors.bottomMargin: 12
                        model: accountController.accounts
                        spacing: 2
                        interactive: false
                        delegate: Rectangle {
                            required property var modelData
                            width: ListView.view.width
                            height: 64
                            color: mouseArea.containsMouse ? "#102943" : "transparent"
                            radius: 8
                            MouseArea { id: mouseArea; anchors.fill: parent; hoverEnabled: true; onClicked: editAccountDialog.edit(modelData) }
                            Row {
                                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12
                                spacing: 10
                                Rectangle { width: 9; height: 9; radius: 5; anchors.verticalCenter: parent.verticalCenter; color: modelData.is_debt ? window.debtColor : window.assetColor }
                                Column {
                                    width: parent.width - 420
                                    anchors.verticalCenter: parent.verticalCenter
                                    Label { text: modelData.name; font.bold: true; font.pixelSize: 15 }
                                    Label { text: modelData.owner + "  •  " + modelData.account_type; color: window.mutedText; font.pixelSize: 12 }
                                }
                                Label {
                                    width: 145
                                    anchors.verticalCenter: parent.verticalCenter
                                    horizontalAlignment: Text.AlignRight
                                    text: modelData.balance
                                    color: modelData.is_debt ? window.debtColor : window.assetColor
                                    font.bold: true; font.pixelSize: 15
                                }
                                Button {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Holdings"
                                    visible: !modelData.is_debt && modelData.account_type !== "Bank"
                                    onClicked: assetBreakdownDialog.openForAccount(modelData)
                                }
                                Button { anchors.verticalCenter: parent.verticalCenter; text: "Edit"; onClicked: editAccountDialog.edit(modelData) }
                                Button {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Remove"
                                    visible: authController.isAdmin
                                    onClicked: {
                                        window.pendingDeleteAccountId = modelData.id
                                        window.pendingDeleteAccountName = modelData.name
                                        deleteAccountConfirmation.open()
                                    }
                                }
                            }
                        }
                    }
                }

                Label {
                    width: parent.width - 48
                    horizontalAlignment: Text.AlignHCenter
                    text: accountController.message
                    color: window.debtColor
                    visible: text.length > 0
                }
                Label {
                    width: parent.width - 48
                    horizontalAlignment: Text.AlignHCenter
                    text: "All family members can update balances. Only administrators can add or remove accounts."
                    color: window.mutedText
                    font.pixelSize: 12
                    bottomPadding: 10
                }
            }
        }

        BudgetDashboard {
            anchors.top: dashboardNavigation.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            opacity: window.budgetPageActive ? 1 : 0
            visible: opacity > 0
            enabled: window.budgetPageActive
            Behavior on opacity { NumberAnimation { duration: 160 } }
        }
    }
}
