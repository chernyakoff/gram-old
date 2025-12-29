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
        BriefIn: {
            description: string;
            offer: string;
            client: string;
            pains: string;
            advantages: string;
            mission: string;
            focus: string;
        };
        BriefOut: {
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
        ProjectIn: {
            name: string;
            dialogLimit: number;
            sendTimeStart: number;
            sendTimeEnd: number;
            firstMessage: string;
            premiumRequired: boolean;
            brief: components["schemas"]["BriefIn"];
            prompt: components["schemas"]["PromptIn"];
            advancedMode: boolean;
            skipOptions: components["schemas"]["ProjectSkipOptions"];
        };
        ProjectOut: {
            id: number;
            name: string;
            dialogLimit: number;
            sendTimeStart: number;
            sendTimeEnd: number;
            firstMessage: string;
            status: boolean;
            premiumRequired: boolean;
            brief: components["schemas"]["BriefOut"];
            prompt: components["schemas"]["PromptOut"];
            skipOptions: components["schemas"]["ProjectSkipOptions"];
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
        PromptIn: {
            role: string;
            context: string;
            init: string;
            engage: string;
            offer: string;
            closing: string;
            instruction: string;
            rules: string;
        };
        PromptOut: {
            role: string;
            context: string;
            init: string;
            engage: string;
            offer: string;
            closing: string;
            instruction: string;
            rules: string;
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
export type BriefIn = components['schemas']['BriefIn'];
export type BriefOut = components['schemas']['BriefOut'];
export type BuyPremiumOut = components['schemas']['BuyPremiumOut'];
export type CardDetails = components['schemas']['CardDetails'];
export type ChatIn = components['schemas']['ChatIn'];
export type ChatOut = components['schemas']['ChatOut'];
export type DialogMessageOut = components['schemas']['DialogMessageOut'];
export type DialogOut = components['schemas']['DialogOut'];
export type DialogStatus = components['schemas']['DialogStatus'];
export type DialogSystemMessageIn = components['schemas']['DialogSystemMessageIn'];
export type EmbedAccountOut = components['schemas']['EmbedAccountOut'];
export type GetBalanceOut = components['schemas']['GetBalanceOut'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type ImpersonateIn = components['schemas']['ImpersonateIn'];
export type ImpersonateOut = components['schemas']['ImpersonateOut'];
export type LicenseIn = components['schemas']['LicenseIn'];
export type LicenseOut = components['schemas']['LicenseOut'];
export type MailingIn = components['schemas']['MailingIn'];
export type MailingListOut = components['schemas']['MailingListOut'];
export type MailingOut = components['schemas']['MailingOut'];
export type MailingStatus = components['schemas']['MailingStatus'];
export type Message = components['schemas']['Message'];
export type MessageRole = components['schemas']['MessageRole'];
export type MessageSender = components['schemas']['MessageSender'];
export type PresignedIn = components['schemas']['PresignedIn'];
export type PresignedOut = components['schemas']['PresignedOut'];
export type ProjectBase = components['schemas']['ProjectBase'];
export type ProjectIn = components['schemas']['ProjectIn'];
export type ProjectOut = components['schemas']['ProjectOut'];
export type ProjectShortOut = components['schemas']['ProjectShortOut'];
export type ProjectSkipOptions = components['schemas']['ProjectSkipOptions'];
export type ProjectStatusIn = components['schemas']['ProjectStatusIn'];
export type PromptIn = components['schemas']['PromptIn'];
export type PromptOut = components['schemas']['PromptOut'];
export type ProxiesBulkCreateIn = components['schemas']['ProxiesBulkCreateIn'];
export type ProxiesCheckIn = components['schemas']['ProxiesCheckIn'];
export type ProxiesCountryIn = components['schemas']['ProxiesCountryIn'];
export type ProxyOut = components['schemas']['ProxyOut'];
export type SetLimitIn = components['schemas']['SetLimitIn'];
export type StatsIn = components['schemas']['StatsIn'];
export type StatsOut = components['schemas']['StatsOut'];
export type SynonimizeIn = components['schemas']['SynonimizeIn'];
export type SynonimizeOut = components['schemas']['SynonimizeOut'];
export type UserLoginIn = components['schemas']['UserLoginIn'];
export type UserLoginOut = components['schemas']['UserLoginOut'];
export type UserMeOut = components['schemas']['UserMeOut'];
export type ValidationError = components['schemas']['ValidationError'];
export type WorkflowOut = components['schemas']['WorkflowOut'];
