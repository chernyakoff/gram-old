export interface components {
    schemas: {
        AccountIn: {
            username: string | null;
            about: string | null;
            channel: string | null;
            firstName: string | null;
            lastName: string | null;
            photos: components["schemas"]["AccountPhotosIn"];
        };
        AccountListOut: {
            id: number;
            name: string;
            phone: string;
        };
        AccountOut: {
            username: string | null;
            about: string | null;
            channel: string | null;
            firstName: string | null;
            lastName: string | null;
            id: number;
            phone: string;
            premium: boolean;
            premiumStopped: boolean;
            twofa: string | null;
            country: string;
            active: boolean;
            busy: boolean;
            createdAt: string;
            photos: components["schemas"]["AccountPhotoOut"][];
            project: components["schemas"]["ProjectBase"] | null;
            status: components["schemas"]["AccountStatus"];
            mutedUntil: string | null;
            outDailyLimit: number;
            isDynamicLimit: boolean;
            dynamicDailyLimit: number | null;
        };
        AccountPhotoOut: {
            id: number;
            url: string;
        };
        AccountPhotosIn: {
            delete: number[];
            upload: string[];
        };
        AccountStatus: "good" | "banned" | "muted" | "frozen" | "exited" | "noproxy";
        AccountsBulkCreateIn: {
            s3path: string;
        };
        AccountsCheckIn: {
            accountIds: number[];
        };
        AiModelIn: {
            id: string;
        };
        AiModelOut: {
            id: string;
            name: string;
            description: string;
            promptPrice: string;
            completionPrice: string;
        };
        AppSettingIn: {
            path: string;
            value: string;
        };
        BalanceIn: {
            username: string;
            amount: number;
        };
        BalanceOut: {
            status: "success" | "error";
            message: string;
        };
        BindProjectIn: {
            projectId: number;
            accountIds: number[];
        };
        Brief: {
            description: string;
            offer: string;
            client: string;
            pains: string;
            advantages: string;
            mission: string;
            focus: string;
        };
        BuyPremiumOut: {
            status: "error" | "success";
            message?: string | null;
            verificationUrl?: string | null;
        };
        CallbackFormIn: {
            name: string;
            phone: string;
            telegram?: string | null;
        };
        CardDetails: {
            number: string;
            month: number;
            year: number;
            cvv: string;
        };
        ChatIn: {
            status: components["schemas"]["DialogStatus"];
            projectId: number;
            messages: components["schemas"]["Message"][];
        };
        ChatOut: {
            text: string;
            status: components["schemas"]["DialogStatus"];
        };
        DayIn: {
            weekday: number;
            enabled: boolean;
            intervals: components["schemas"]["IntervalIn"][];
        };
        DayMeeting: {
            date: string;
            count: number;
        };
        DayOut: {
            weekday: number;
            enabled: boolean;
            intervals: components["schemas"]["IntervalOut"][];
        };
        DialogIn: {
            projectId?: number | null;
            accountId?: number | null;
            mailingId?: number | null;
        };
        DialogMessageOut: {
            sender: components["schemas"]["MessageSender"];
            text: string;
            ack: boolean;
            createdAt: string;
        };
        DialogOut: {
            id: number;
            status: components["schemas"]["DialogStatus"];
            recipient: string;
            account: string;
            project: string;
            startedAt: string;
        };
        DialogStatus: "init" | "engage" | "offer" | "closing" | "complete" | "negative" | "operator" | "manual";
        DialogSystemMessageIn: {
            dialogId: number;
            message: string;
        };
        DialogsDownloadIn: {
            username: string;
            status?: components["schemas"]["DialogStatus"] | null;
        };
        EmbedAccountOut: {
            id: number;
            phone: string;
            username: string | null;
        };
        GetBalanceOut: {
            openrouter: number;
            users: number;
        };
        HTTPValidationError: {
            detail?: components["schemas"]["ValidationError"][];
        };
        ImpersonateIn: {
            username: string;
        };
        ImpersonateOut: {
            access: string;
        };
        IntervalIn: {
            start: string;
            end: string;
        };
        IntervalOut: {
            start: string;
            end: string;
        };
        LicenseIn: {
            username: string;
            days: number;
        };
        LicenseOut: {
            status: "success" | "error";
            message: string;
        };
        MailingIn: {
            name: string;
            projectId: number;
            recipients: string[];
        };
        MailingListOut: {
            id: number;
            name: string;
        };
        MailingOut: {
            id: number;
            project: components["schemas"]["ProjectBase"];
            name: string;
            status: components["schemas"]["MailingStatus"];
            startedAt: string | null;
            sentCount: number;
            totalCount: number;
            failedCount: number;
        };
        MailingStatus: "draft" | "running" | "finished" | "cancelled";
        MeetingDuration: {
            value: number;
        };
        MeetingOut: {
            id: number;
            startAt: string;
            endAt: string;
            username: string;
            dialogId: number;
        };
        Message: {
            role: components["schemas"]["MessageRole"];
            text: string;
        };
        MessageRole: "user" | "assistant" | "system";
        MessageSender: "account" | "recipient" | "system";
        PresignedIn: {
            path: string;
            filename: string;
        };
        PresignedOut: {
            s3path: string;
            url: string;
        };
        ProjectBase: {
            id: number;
            name: string;
        };
        ProjectCreateIn: {
            name: string;
        };
        ProjectDocumentIn: {
            filename: string;
            fileSize: number;
            storagePath: string;
            contentType: string;
        };
        ProjectDocumentOut: {
            id: number;
            filename: string;
            fileSize: number;
            url: string;
            contentType: string;
        };
        ProjectFileIn: {
            filename: string;
            fileSize: number;
            storagePath: string;
            contentType: string;
        };
        ProjectFileOut: {
            id: number;
            title: string;
            filename: string;
            fileSize: number;
            url: string;
            contentType: string;
            status?: components["schemas"]["ProjectFileStatus"] | null;
        };
        ProjectFileStatus: "engage" | "offer" | "closing" | "complete";
        ProjectFileUpdateIn: {
            title: string;
            filename: string;
            status?: components["schemas"]["ProjectFileStatus"] | null;
        };
        ProjectSettings: {
            name: string;
            dialogLimit: number;
            sendTimeStart: number;
            sendTimeEnd: number;
            firstMessage: string;
            premiumRequired: boolean;
        };
        ProjectShortOut: {
            id: number;
            name: string;
            status: boolean;
        };
        ProjectSkipOptions: {
            engage: boolean;
            offer: boolean;
            closing: boolean;
        };
        ProjectStatusIn: {
            status: boolean;
        };
        ProjectStatusOut: {
            result: "success" | "error";
            errors: string[];
        };
        Prompt: {
            role: string;
            context: string;
            init: string;
            engage: string;
            offer: string;
            closing: string;
            instruction: string;
            rules: string;
            skipOptions: components["schemas"]["ProjectSkipOptions"];
        };
        ProxiesBulkCreateIn: {
            proxies: string[];
        };
        ProxiesCheckIn: {
            ids: number[];
        };
        ProxiesCountryIn: {
            country: string;
            ids: number[];
        };
        ProxyOut: {
            id: number;
            host: string;
            port: number;
            username: string;
            password: string;
            country: string;
            createdAt: string;
            active: boolean;
            failures: number;
            account?: components["schemas"]["EmbedAccountOut"] | null;
        };
        ScheduleIn: {
            schedule: components["schemas"]["DayIn"][];
        };
        ScheduleOut: {
            schedule: components["schemas"]["DayOut"][];
            timezone: string;
            disabledMonthDays: number[];
            meetingDuration: number;
        };
        SetLimitIn: {
            outDailyLimit: number;
            accountIds: number[];
        };
        StatsIn: {
            dateFrom: string;
            dateTo: string;
            projectId?: number | null;
            accountId?: number | null;
            mailingId?: number | null;
        };
        StatsOut: {
            init: number[];
            engage: number[];
            offer: number[];
            closing: number[];
            complete: number[];
            negative: number[];
            operator: number[];
            manual: number[];
        };
        SynonimizeIn: {
            text: string;
        };
        SynonimizeOut: {
            text: string;
            error?: string | null;
        };
        ToggleDayIn: {
            day: number;
        };
        UserLoginIn: {
            id: number;
            authDate: number;
            hash: string;
            firstName: string | null;
            lastName: string | null;
            username: string | null;
            photoUrl: string | null;
        };
        UserLoginOut: {
            accessToken: string;
        };
        UserMeOut: {
            id: number;
            username: string | null;
            firstName: string | null;
            lastName: string | null;
            photoUrl: string | null;
            role: string;
            balance: number;
            hasLicense: boolean;
            impersonated?: boolean | null;
            realUserId?: number | null;
        };
        UserTimezone: {
            timezone: string;
        };
        ValidationError: {
            loc: (string | number)[];
            msg: string;
            type: string;
        };
        WorkflowOut: {
            id: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type AccountIn = components['schemas']['AccountIn'];
export type AccountListOut = components['schemas']['AccountListOut'];
export type AccountOut = components['schemas']['AccountOut'];
export type AccountPhotoOut = components['schemas']['AccountPhotoOut'];
export type AccountPhotosIn = components['schemas']['AccountPhotosIn'];
export type AccountStatus = components['schemas']['AccountStatus'];
export type AccountsBulkCreateIn = components['schemas']['AccountsBulkCreateIn'];
export type AccountsCheckIn = components['schemas']['AccountsCheckIn'];
export type AiModelIn = components['schemas']['AiModelIn'];
export type AiModelOut = components['schemas']['AiModelOut'];
export type AppSettingIn = components['schemas']['AppSettingIn'];
export type BalanceIn = components['schemas']['BalanceIn'];
export type BalanceOut = components['schemas']['BalanceOut'];
export type BindProjectIn = components['schemas']['BindProjectIn'];
export type Brief = components['schemas']['Brief'];
export type BuyPremiumOut = components['schemas']['BuyPremiumOut'];
export type CallbackFormIn = components['schemas']['CallbackFormIn'];
export type CardDetails = components['schemas']['CardDetails'];
export type ChatIn = components['schemas']['ChatIn'];
export type ChatOut = components['schemas']['ChatOut'];
export type DayIn = components['schemas']['DayIn'];
export type DayMeeting = components['schemas']['DayMeeting'];
export type DayOut = components['schemas']['DayOut'];
export type DialogIn = components['schemas']['DialogIn'];
export type DialogMessageOut = components['schemas']['DialogMessageOut'];
export type DialogOut = components['schemas']['DialogOut'];
export type DialogStatus = components['schemas']['DialogStatus'];
export type DialogSystemMessageIn = components['schemas']['DialogSystemMessageIn'];
export type DialogsDownloadIn = components['schemas']['DialogsDownloadIn'];
export type EmbedAccountOut = components['schemas']['EmbedAccountOut'];
export type GetBalanceOut = components['schemas']['GetBalanceOut'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type ImpersonateIn = components['schemas']['ImpersonateIn'];
export type ImpersonateOut = components['schemas']['ImpersonateOut'];
export type IntervalIn = components['schemas']['IntervalIn'];
export type IntervalOut = components['schemas']['IntervalOut'];
export type LicenseIn = components['schemas']['LicenseIn'];
export type LicenseOut = components['schemas']['LicenseOut'];
export type MailingIn = components['schemas']['MailingIn'];
export type MailingListOut = components['schemas']['MailingListOut'];
export type MailingOut = components['schemas']['MailingOut'];
export type MailingStatus = components['schemas']['MailingStatus'];
export type MeetingDuration = components['schemas']['MeetingDuration'];
export type MeetingOut = components['schemas']['MeetingOut'];
export type Message = components['schemas']['Message'];
export type MessageRole = components['schemas']['MessageRole'];
export type MessageSender = components['schemas']['MessageSender'];
export type PresignedIn = components['schemas']['PresignedIn'];
export type PresignedOut = components['schemas']['PresignedOut'];
export type ProjectBase = components['schemas']['ProjectBase'];
export type ProjectCreateIn = components['schemas']['ProjectCreateIn'];
export type ProjectDocumentIn = components['schemas']['ProjectDocumentIn'];
export type ProjectDocumentOut = components['schemas']['ProjectDocumentOut'];
export type ProjectFileIn = components['schemas']['ProjectFileIn'];
export type ProjectFileOut = components['schemas']['ProjectFileOut'];
export type ProjectFileStatus = components['schemas']['ProjectFileStatus'];
export type ProjectFileUpdateIn = components['schemas']['ProjectFileUpdateIn'];
export type ProjectSettings = components['schemas']['ProjectSettings'];
export type ProjectShortOut = components['schemas']['ProjectShortOut'];
export type ProjectSkipOptions = components['schemas']['ProjectSkipOptions'];
export type ProjectStatusIn = components['schemas']['ProjectStatusIn'];
export type ProjectStatusOut = components['schemas']['ProjectStatusOut'];
export type Prompt = components['schemas']['Prompt'];
export type ProxiesBulkCreateIn = components['schemas']['ProxiesBulkCreateIn'];
export type ProxiesCheckIn = components['schemas']['ProxiesCheckIn'];
export type ProxiesCountryIn = components['schemas']['ProxiesCountryIn'];
export type ProxyOut = components['schemas']['ProxyOut'];
export type ScheduleIn = components['schemas']['ScheduleIn'];
export type ScheduleOut = components['schemas']['ScheduleOut'];
export type SetLimitIn = components['schemas']['SetLimitIn'];
export type StatsIn = components['schemas']['StatsIn'];
export type StatsOut = components['schemas']['StatsOut'];
export type SynonimizeIn = components['schemas']['SynonimizeIn'];
export type SynonimizeOut = components['schemas']['SynonimizeOut'];
export type ToggleDayIn = components['schemas']['ToggleDayIn'];
export type UserLoginIn = components['schemas']['UserLoginIn'];
export type UserLoginOut = components['schemas']['UserLoginOut'];
export type UserMeOut = components['schemas']['UserMeOut'];
export type UserTimezone = components['schemas']['UserTimezone'];
export type ValidationError = components['schemas']['ValidationError'];
export type WorkflowOut = components['schemas']['WorkflowOut'];
