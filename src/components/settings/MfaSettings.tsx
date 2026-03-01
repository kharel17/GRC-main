"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, Shield, QrCode, CheckCircle2, AlertCircle } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/hooks/useAuth";

export function MfaSettings() {
    const { user } = useAuth();
    const [mfaEnabled, setMfaEnabled] = useState(false);
    const [showSetup, setShowSetup] = useState(false);
    const [loading, setLoading] = useState(false);
    const [qrCode, setQrCode] = useState("");
    const [secret, setSecret] = useState("");
    const [code, setCode] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // In a real app, we'd fetch the user profile to get the most up-to-date MFA status
    useEffect(() => {
        if (user) {
            // Fetch fresh user data to see if MFA is enabled
            const checkMfaStatus = async () => {
                try {
                    const userData = await api.get<any>('/auth/me');
                    setMfaEnabled(userData.mfa_enabled);
                } catch (err) {
                    console.error("Failed to fetch MFA status", err);
                }
            };
            checkMfaStatus();
        }
    }, [user]);

    const handleStartSetup = async () => {
        setLoading(true);
        setError("");
        try {
            const data = await api.post<any>("/auth/mfa/setup");
            setQrCode(data.qr_code);
            setSecret(data.secret);
            setShowSetup(true);
        } catch (err: any) {
            setError(err.message || "Failed to start MFA setup");
        } finally {
            setLoading(false);
        }
    };

    const handleVerifySetup = async () => {
        if (code.length !== 6) {
            setError("Please enter a 6-digit code");
            return;
        }

        setLoading(true);
        setError("");
        try {
            await api.post("/auth/mfa/enable", { code });
            setMfaEnabled(true);
            setShowSetup(false);
            setSuccess("MFA has been successfully enabled!");
        } catch (err: any) {
            setError(err.message || "Verification failed. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    if (mfaEnabled) {
        return (
            <div className="flex items-center justify-between p-4 bg-green-50 border border-green-100 rounded-lg">
                <div>
                    <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                        <p className="font-medium text-green-900">Two-Factor Authentication is Active</p>
                    </div>
                    <p className="text-xs text-green-700 mt-1">Your account is protected with TOTP authentication.</p>
                </div>
                <Badge className="bg-green-600">Active</Badge>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {success && (
                <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg text-sm">
                    <CheckCircle2 className="h-4 w-4" />
                    {success}
                </div>
            )}

            {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                    <AlertCircle className="h-4 w-4" />
                    {error}
                </div>
            )}

            {!showSetup ? (
                <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-transparent hover:border-slate-200 transition-colors">
                    <div>
                        <p className="font-medium text-sm flex items-center gap-2">
                            <Shield className="h-4 w-4 text-slate-500" />
                            Two-Factor Authentication
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">Add an extra layer of security to your account.</p>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleStartSetup} disabled={loading}>
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Set Up MFA"}
                    </Button>
                </div>
            ) : (
                <Card className="border-blue-100 bg-blue-50/30">
                    <CardHeader className="pb-4">
                        <CardTitle className="text-sm font-semibold flex items-center gap-2">
                            <QrCode className="h-4 w-4 text-blue-600" />
                            Scan QR Code
                        </CardTitle>
                        <CardDescription className="text-xs">
                            Scan this code with your authenticator app (e.g., Google Authenticator, Authy).
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex flex-col items-center justify-center p-4 bg-white rounded-lg border border-blue-100 shadow-sm w-fit mx-auto">
                            {qrCode ? (
                                <img src={`data:image/png;base64,${qrCode}`} alt="MFA QR Code" className="w-40 h-40" />
                            ) : (
                                <div className="w-40 h-40 flex items-center justify-center bg-slate-100 animate-pulse rounded" />
                            )}
                            <div className="mt-3 font-mono text-[10px] text-slate-500 bg-slate-50 px-2 py-1 rounded">
                                Secret: {secret}
                            </div>
                        </div>

                        <div className="space-y-2 max-w-[240px] mx-auto">
                            <Label htmlFor="mfaCode" className="text-xs font-medium text-center block">
                                Verification Code
                            </Label>
                            <Input
                                id="mfaCode"
                                placeholder="000000"
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                                className="text-center tracking-widest bg-white"
                                disabled={loading}
                            />
                        </div>

                        <div className="flex gap-2 justify-center pt-2">
                            <Button variant="ghost" size="sm" onClick={() => setShowSetup(false)} disabled={loading}>
                                Cancel
                            </Button>
                            <Button size="sm" onClick={handleVerifySetup} disabled={loading || code.length !== 6}>
                                {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                Verify & Enable
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
