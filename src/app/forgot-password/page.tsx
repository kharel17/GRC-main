"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";
import { api } from "@/lib/api-client";

export default function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState(false);
    const [debugToken, setDebugToken] = useState(""); // For demo/local testing

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!email) {
            setError("Email is required");
            return;
        }

        setIsLoading(true);
        setError("");
        try {
            const response = await api.post<any>("/auth/forgot-password", { email });
            setSuccess(true);
            if (response.debug_token) {
                setDebugToken(response.debug_token);
            }
        } catch (err: any) {
            setError(err.message || "An error occurred. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
            <div className="w-full max-w-md">
                <Card className="border-0 shadow-lg">
                    <CardHeader className="space-y-1">
                        <Link
                            href="/login"
                            className="text-xs text-slate-500 hover:text-blue-600 flex items-center gap-1 mb-4 transition-colors w-fit"
                        >
                            <ArrowLeft className="h-3 w-3" />
                            Back to login
                        </Link>
                        <CardTitle className="text-2xl">Reset Password</CardTitle>
                        <CardDescription>
                            Enter your email address and we'll send you a link to reset your password.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {success ? (
                            <div className="space-y-6">
                                <div className="flex flex-col items-center text-center space-y-3 p-6 bg-green-50 rounded-xl border border-green-100">
                                    <CheckCircle2 className="h-12 w-12 text-green-600" />
                                    <div className="space-y-1">
                                        <h3 className="font-semibold text-green-900">Check your email</h3>
                                        <p className="text-sm text-green-700">
                                            We've sent a password reset link to <span className="font-medium">{email}</span>.
                                        </p>
                                    </div>
                                </div>

                                {debugToken && (
                                    <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg space-y-2">
                                        <p className="text-[10px] font-bold text-blue-700 uppercase tracking-wider">Demo / Debug Info:</p>
                                        <p className="text-xs text-blue-800">In a production app, the link would be in your email. For this demo, here is your reset link:</p>
                                        <Link
                                            href={`/reset-password?token=${debugToken}`}
                                            className="text-xs font-mono text-blue-600 underline break-all block p-2 bg-white rounded border border-blue-200"
                                        >
                                            /reset-password?token={debugToken}
                                        </Link>
                                    </div>
                                )}

                                <Button variant="outline" className="w-full" asChild>
                                    <Link href="/login">Return to login</Link>
                                </Button>
                            </div>
                        ) : (
                            <form onSubmit={handleSubmit} className="space-y-4">
                                {error && (
                                    <div className="flex gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                                        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                                        <p className="text-sm text-red-700">{error}</p>
                                    </div>
                                )}

                                <div className="space-y-2">
                                    <Label htmlFor="email" className="text-sm font-medium">Email Address</Label>
                                    <Input
                                        id="email"
                                        type="email"
                                        placeholder="name@company.com"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        disabled={isLoading}
                                        className="bg-slate-50"
                                    />
                                </div>

                                <Button type="submit" className="w-full mt-2" disabled={isLoading}>
                                    {isLoading ? (
                                        <>
                                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                            Sending Link...
                                        </>
                                    ) : (
                                        "Send Reset Link"
                                    )}
                                </Button>
                            </form>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
