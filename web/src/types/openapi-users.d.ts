export interface components {
    schemas: {
        BalanceIn: {
            username: string;
            amount: number;
        };
        BalanceOut: {
            status: "success" | "error";
            message: string;
        };
        CreateUserIn: {
            id: number;
            username?: string | null;
            firstName?: string | null;
            lastName?: string | null;
            photoUrl?: string | null;
            role?: components["schemas"]["Role"] | null;
            licenseEndDate?: string | null;
            balance?: number | null;
            refCode?: string | null;
            orApiKey?: string | null;
            orApiHash?: string | null;
            orModel?: string | null;
        };
        CreateUserOut: {
            status: "created" | "updated";
            userId: number;
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
        InternalDebitBalanceIn: {
            userId: number;
            amountKopecks: number;
        };
        InternalDebitBalanceOut: {
            status: "ok" | "insufficient_funds" | "not_found";
            balanceKopecks: number | null;
        };
        InternalSetOpenRouterIn: {
            userId: number;
            apiKey?: string | null;
            apiHash?: string | null;
            model?: string | null;
        };
        InternalUserStateIn: {
            userId: number;
        };
        InternalUserStateOut: {
            userId: number;
            balanceKopecks: number;
            apiKey: string | null;
            apiHash: string | null;
            model: string | null;
        };
        LicenseIn: {
            username: string;
            days: number;
        };
        LicenseOut: {
            status: "success" | "error";
            message: string;
        };
        PartnerOut: {
            id: number;
            username?: string | null;
            firstName?: string | null;
            lastName?: string | null;
            photoUrl?: string | null;
            referredBy?: components["schemas"]["UserBasicOut"] | null;
            referrals: components["schemas"]["UserBasicOut"][];
        };
        Role: 0 | 7;
        UserBalanceOut: {
            balanceKopecks: number;
            balanceRub: number;
        };
        UserBasicOut: {
            id: number;
            username?: string | null;
            firstName?: string | null;
            lastName?: string | null;
            photoUrl?: string | null;
        };
        UserLoginIn: {
            id: number;
            authDate: number;
            hash: string;
            firstName: string | null;
            lastName: string | null;
            username: string | null;
            photoUrl: string | null;
            inviteRefCode?: string | null;
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
            refCode: string | null;
            impersonated?: boolean | null;
            realUserId?: number | null;
        };
        UserOpenRouterSettingsIn: {
            apiKey?: string | null;
            apiHash?: string | null;
            model?: string | null;
        };
        UserOpenRouterSettingsOut: {
            apiKey: string | null;
            apiHash: string | null;
            model: string | null;
        };
        ValidationError: {
            loc: (string | number)[];
            msg: string;
            type: string;
            input?: unknown;
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type BalanceIn = components['schemas']['BalanceIn'];
export type BalanceOut = components['schemas']['BalanceOut'];
export type CreateUserIn = components['schemas']['CreateUserIn'];
export type CreateUserOut = components['schemas']['CreateUserOut'];
export type HttpValidationError = components['schemas']['HTTPValidationError'];
export type ImpersonateIn = components['schemas']['ImpersonateIn'];
export type ImpersonateOut = components['schemas']['ImpersonateOut'];
export type InternalDebitBalanceIn = components['schemas']['InternalDebitBalanceIn'];
export type InternalDebitBalanceOut = components['schemas']['InternalDebitBalanceOut'];
export type InternalSetOpenRouterIn = components['schemas']['InternalSetOpenRouterIn'];
export type InternalUserStateIn = components['schemas']['InternalUserStateIn'];
export type InternalUserStateOut = components['schemas']['InternalUserStateOut'];
export type LicenseIn = components['schemas']['LicenseIn'];
export type LicenseOut = components['schemas']['LicenseOut'];
export type PartnerOut = components['schemas']['PartnerOut'];
export type Role = components['schemas']['Role'];
export type UserBalanceOut = components['schemas']['UserBalanceOut'];
export type UserBasicOut = components['schemas']['UserBasicOut'];
export type UserLoginIn = components['schemas']['UserLoginIn'];
export type UserLoginOut = components['schemas']['UserLoginOut'];
export type UserMeOut = components['schemas']['UserMeOut'];
export type UserOpenRouterSettingsIn = components['schemas']['UserOpenRouterSettingsIn'];
export type UserOpenRouterSettingsOut = components['schemas']['UserOpenRouterSettingsOut'];
export type ValidationError = components['schemas']['ValidationError'];
