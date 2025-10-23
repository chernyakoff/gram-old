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
        AccountOut: {
            username: string | null;
            about: string | null;
            channel: string | null;
            firstName: string | null;
            lastName: string | null;
            id: number;
            phone: string;
            premium: boolean;
            twofa: string | null;
            country: string;
            active: boolean;
            busy: boolean;
            createdAt: string;
            photos: components["schemas"]["AccountPhotoOut"][];
            project: components["schemas"]["ProjectBase"] | null;
        };
        AccountPhotoOut: {
            id: number;
            url: string;
        };
        AccountPhotosIn: {
            delete: number[];
            upload: string[];
        };
        AccountsBulkCreateIn: {
            s3path: string;
        };
        BindProjectIn: {
            projectId: number;
            accountIds: number[];
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
        ContactOut: {
            uid: number;
            id: number | null;
            username: string;
            firstName: string | null;
            lastName: string | null;
            createdAt: string;
            project: components["schemas"]["ProjectBase"];
        };
        ContactsBulkCreateIn: {
            projectId: number;
            usernames: string[];
        };
        ContactsBulkCreateOut: {
            total: number;
            added: number;
        };
        DialogMessageOut: {
            sender: components["schemas"]["MessageSender"];
            text: string;
            createdAt: string;
        };
        DialogOut: {
            id: number;
            status: components["schemas"]["DialogStatus"];
            recipient: string;
            startedAt: string;
        };
        DialogStatus: "init" | "engage" | "offer" | "closing";
        HTTPValidationError: {
            detail?: components["schemas"]["ValidationError"][];
        };
        MailingIn: {
            name: string;
            projectId: number;
            recipients: string[];
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
            outDailyLimit: number;
            sendTimeStart: number;
            sendTimeEnd: number;
            firstMessage: string;
            role: string;
            context: string;
            init: string;
            engage: string;
            offer: string;
            closing: string;
            instruction: string;
            rules: string;
        };
        ProjectOut: {
            name: string;
            dialogLimit: number;
            outDailyLimit: number;
            sendTimeStart: number;
            sendTimeEnd: number;
            firstMessage: string;
            role: string;
            context: string;
            init: string;
            engage: string;
            offer: string;
            closing: string;
            instruction: string;
            rules: string;
            id: number;
        };
        ProjectShortOut: {
            id: number;
            name: string;
            status: boolean;
        };
        ProjectStatusIn: {
            status: boolean;
        };
        ProxiesBulkCreateIn: {
            proxies: string[];
        };
        ProxyOut: {
            id: number;
            host: string;
            port: number;
            username: string;
            password: string;
            country: string;
            createdAt: string;
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
        UserOut: {
            id: number;
            username: string | null;
            firstName: string | null;
            lastName: string | null;
            photoUrl: string | null;
            role: string;
            hasLicense: boolean;
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
export type AccountOut = components['schemas']['AccountOut'];
export type AccountPhotoOut = components['schemas']['AccountPhotoOut'];
export type AccountPhotosIn = components['schemas']['AccountPhotosIn'];
export type AccountsBulkCreateIn = components['schemas']['AccountsBulkCreateIn'];
export type BindProjectIn = components['schemas']['BindProjectIn'];
export type ChatIn = components['schemas']['ChatIn'];
export type ChatOut = components['schemas']['ChatOut'];
export type ContactOut = components['schemas']['ContactOut'];
export type ContactsBulkCreateIn = components['schemas']['ContactsBulkCreateIn'];
export type ContactsBulkCreateOut = components['schemas']['ContactsBulkCreateOut'];
export type DialogMessageOut = components['schemas']['DialogMessageOut'];
export type DialogOut = components['schemas']['DialogOut'];
export type DialogStatus = components['schemas']['DialogStatus'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type MailingIn = components['schemas']['MailingIn'];
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
export type ProjectStatusIn = components['schemas']['ProjectStatusIn'];
export type ProxiesBulkCreateIn = components['schemas']['ProxiesBulkCreateIn'];
export type ProxyOut = components['schemas']['ProxyOut'];
export type UserLoginIn = components['schemas']['UserLoginIn'];
export type UserLoginOut = components['schemas']['UserLoginOut'];
export type UserOut = components['schemas']['UserOut'];
export type ValidationError = components['schemas']['ValidationError'];
export type WorkflowOut = components['schemas']['WorkflowOut'];
