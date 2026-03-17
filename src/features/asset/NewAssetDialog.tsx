"use client";

import { useState, useEffect } from "react";
import { 
    Dialog, 
    DialogContent, 
    DialogHeader, 
    DialogTitle, 
    DialogFooter 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { 
    Select, 
    SelectContent, 
    SelectItem, 
    SelectTrigger, 
    SelectValue 
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { createAsset, fetchUsers } from "@/lib/data-service";
import { Loader2, Plus } from "lucide-react";
import { User } from "@/types";

interface NewAssetDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

export function NewAssetDialog({ open, onOpenChange, onSuccess }: NewAssetDialogProps) {
    const [loading, setLoading] = useState(false);
    const [users, setUsers] = useState<User[]>([]);
    
    const [formData, setFormData] = useState({
        name: "",
        description: "",
        type: "data",
        classification: "internal",
        criticality: "medium",
        location: "",
        confidentiality: "medium",
        integrity: "medium",
        availability: "medium",
        owner_id: ""
    });

    useEffect(() => {
        if (open) {
            loadUsers();
        }
    }, [open]);

    const loadUsers = async () => {
        try {
            const data = await fetchUsers();
            setUsers(data);
        } catch (error) {
            console.error("Failed to load users", error);
        }
    };

    const resetForm = () => {
        setFormData({
            name: "",
            description: "",
            type: "data",
            classification: "internal",
            criticality: "medium",
            location: "",
            confidentiality: "medium",
            integrity: "medium",
            availability: "medium",
            owner_id: ""
        });
    };

    const handleOpenChange = (newOpen: boolean) => {
        if (!newOpen) {
            resetForm();
        }
        onOpenChange(newOpen);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!formData.name || !formData.owner_id) {
            toast.error("Please fill in all required fields (Name and Owner)");
            return;
        }

        setLoading(true);
        try {
            await createAsset(formData as any);
            toast.success("Asset registered successfully");
            handleOpenChange(false);
            if (onSuccess) onSuccess();
        } catch (error: any) {
            toast.error(error.message || "Failed to register asset");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleOpenChange}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Register New Asset</DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4 py-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2 col-span-2">
                            <Label htmlFor="name">Asset Name *</Label>
                            <Input 
                                id="name" 
                                placeholder="e.g. Primary Production Database" 
                                value={formData.name}
                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                required
                            />
                        </div>
                        
                        <div className="space-y-2 col-span-2">
                            <Label htmlFor="description">Description</Label>
                            <Textarea 
                                id="description" 
                                placeholder="Describe the asset purposes and importance..." 
                                value={formData.description}
                                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="type">Asset Type</Label>
                            <Select 
                                value={formData.type} 
                                onValueChange={(v) => setFormData({ ...formData, type: v })}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="data">Data</SelectItem>
                                    <SelectItem value="software">Software</SelectItem>
                                    <SelectItem value="hardware">Hardware</SelectItem>
                                    <SelectItem value="service">Service</SelectItem>
                                    <SelectItem value="personnel">Personnel</SelectItem>
                                    <SelectItem value="physical">Physical Asset</SelectItem>
                                    <SelectItem value="server">Server</SelectItem>
                                    <SelectItem value="db">Database</SelectItem>
                                    <SelectItem value="app">Application</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="owner">Asset Owner *</Label>
                            <Select 
                                value={formData.owner_id} 
                                onValueChange={(v) => setFormData({ ...formData, owner_id: v })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select owner" />
                                </SelectTrigger>
                                <SelectContent>
                                    {users.map(user => (
                                        <SelectItem key={user.id} value={user.id}>
                                            {user.full_name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="classification">Classification</Label>
                            <Select 
                                value={formData.classification} 
                                onValueChange={(v) => setFormData({ ...formData, classification: v })}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="public">Public</SelectItem>
                                    <SelectItem value="internal">Internal Only</SelectItem>
                                    <SelectItem value="confidential">Confidential</SelectItem>
                                    <SelectItem value="restricted">Restricted</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="criticality">Criticality</Label>
                            <Select 
                                value={formData.criticality} 
                                onValueChange={(v) => setFormData({ ...formData, criticality: v })}
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="low">Low</SelectItem>
                                    <SelectItem value="medium">Medium</SelectItem>
                                    <SelectItem value="high">High</SelectItem>
                                    <SelectItem value="critical">Critical</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="space-y-2 col-span-2">
                            <Label htmlFor="location">Physical/Logical Location</Label>
                            <Input 
                                id="location" 
                                placeholder="e.g. AWS us-east-1, Data Center A" 
                                value={formData.location}
                                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                            />
                        </div>

                        <div className="col-span-2 pt-2 border-t mt-2">
                            <Label className="text-xs font-bold uppercase text-muted-foreground">ISO 27001 CIA Assessment</Label>
                            <div className="grid grid-cols-3 gap-2 mt-2">
                                <div className="space-y-1">
                                    <Label className="text-[10px]">Confidentiality</Label>
                                    <Select 
                                        value={formData.confidentiality} 
                                        onValueChange={(v) => setFormData({ ...formData, confidentiality: v })}
                                    >
                                        <SelectTrigger className="h-8 text-xs">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="low">Low</SelectItem>
                                            <SelectItem value="medium">Medium</SelectItem>
                                            <SelectItem value="high">High</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-[10px]">Integrity</Label>
                                    <Select 
                                        value={formData.integrity} 
                                        onValueChange={(v) => setFormData({ ...formData, integrity: v })}
                                    >
                                        <SelectTrigger className="h-8 text-xs">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="low">Low</SelectItem>
                                            <SelectItem value="medium">Medium</SelectItem>
                                            <SelectItem value="high">High</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-1">
                                    <Label className="text-[10px]">Availability</Label>
                                    <Select 
                                        value={formData.availability} 
                                        onValueChange={(v) => setFormData({ ...formData, availability: v })}
                                    >
                                        <SelectTrigger className="h-8 text-xs">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="low">Low</SelectItem>
                                            <SelectItem value="medium">Medium</SelectItem>
                                            <SelectItem value="high">High</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </div>
                    </div>

                    <DialogFooter className="pt-4 mt-2 border-t">
                        <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                            Cancel
                        </Button>
                        <Button type="submit" disabled={loading}>
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Register Asset
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
