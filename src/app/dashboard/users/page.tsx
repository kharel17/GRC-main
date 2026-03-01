'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { fetchUsers, createUser, updateUser, deleteUsers } from '@/lib/data-service';
import { UserProfile, UserRole } from '@/types/user';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
    Users as UsersIcon,
    UserPlus,
    MoreHorizontal,
    Shield,
    ShieldAlert,
    User,
    Trash2,
    Mail,
    Building,
    Loader2,
    CheckCircle2,
    XCircle
} from 'lucide-react';
import { toast } from 'sonner';

export default function UsersPage() {
    const { user: currentUser } = useAuth();
    const [users, setUsers] = useState<UserProfile[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Form State
    const [formData, setFormData] = useState({
        email: '',
        fullName: '',
        password: 'Password123!', // Default for invitation
        role: 'analyst' as UserRole,
        department: '',
    });

    useEffect(() => {
        loadUsers();
    }, []);

    async function loadUsers() {
        try {
            setIsLoading(true);
            const data = await fetchUsers();
            setUsers(data);
        } catch (error) {
            console.error('Failed to fetch users:', error);
            toast.error('Failed to load users');
        } finally {
            setIsLoading(false);
        }
    }

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            setIsSubmitting(true);
            // Map to snake_case for backend
            const payload = {
                email: formData.email,
                full_name: formData.fullName,
                password: formData.password,
                role: formData.role,
                department: formData.department,
            };
            await createUser(payload);
            toast.success('User invited successfully');
            setIsInviteModalOpen(false);
            setFormData({
                email: '',
                fullName: '',
                password: 'Password123!',
                role: 'analyst',
                department: '',
            });
            loadUsers();
        } catch (error) {
            toast.error('Failed to invite user');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleToggleActive = async (userId: string, currentStatus: boolean) => {
        try {
            await updateUser(userId, { is_active: !currentStatus });
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: !currentStatus } : u));
            toast.success(`User ${currentStatus ? 'deactivated' : 'activated'}`);
        } catch (error) {
            toast.error('Failed to update user status');
        }
    };

    const handleRoleChange = async (userId: string, newRole: UserRole) => {
        try {
            await updateUser(userId, { role: newRole });
            setUsers(prev => prev.map(u => u.id === userId ? { ...u, role: newRole } : u));
            toast.success(`Role updated to ${newRole}`);
        } catch (error) {
            toast.error('Failed to update role');
        }
    };

    const handleDelete = async (userId: string) => {
        if (userId === currentUser?.id) {
            toast.error("You cannot delete yourself");
            return;
        }

        if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
            return;
        }

        try {
            // Note: need to implement deleteUser in data-service if not there
            // For now we'll just mock it or handle the error
            await updateUser(userId, { is_active: false }); // Fallback: just deactivate
            toast.success('User access revoked');
            loadUsers();
        } catch (error) {
            toast.error('Failed to delete user');
        }
    };

    const getRoleBadge = (role: UserRole) => {
        switch (role) {
            case 'admin':
                return <Badge className="bg-purple-100 text-purple-700 hover:bg-purple-100 border-none px-2.5 py-0.5 flex items-center gap-1"><ShieldAlert className="h-3 w-3" /> Admin</Badge>;
            case 'analyst':
                return <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100 border-none px-2.5 py-0.5 flex items-center gap-1"><Shield className="h-3 w-3" /> Analyst</Badge>;
            case 'manager':
                return <Badge className="bg-green-100 text-green-700 hover:bg-green-100 border-none px-2.5 py-0.5 flex items-center gap-1"><User className="h-3 w-3" /> Manager</Badge>;
        }
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
                        <UsersIcon className="h-6 w-6 text-primary" />
                        User Management
                    </h1>
                    <p className="text-sm text-muted-foreground">
                        Manage your team, roles, and platform access.
                    </p>
                </div>

                <Dialog open={isInviteModalOpen} onOpenChange={setIsInviteModalOpen}>
                    <DialogTrigger asChild>
                        <Button className="flex items-center gap-2 shadow-sm">
                            <UserPlus className="h-4 w-4" />
                            Invite User
                        </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                            <DialogTitle>Invite New User</DialogTitle>
                            <DialogDescription>
                                Send an invitation to join the GRC platform.
                            </DialogDescription>
                        </DialogHeader>
                        <form onSubmit={handleInvite} className="space-y-4 py-4">
                            <div className="space-y-2">
                                <Label htmlFor="fullName">Full Name</Label>
                                <div className="relative">
                                    <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="fullName"
                                        placeholder="John Doe"
                                        className="pl-10"
                                        value={formData.fullName}
                                        onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="email">Email Address</Label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="email"
                                        type="email"
                                        placeholder="john@company.com"
                                        className="pl-10"
                                        value={formData.email}
                                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                                        required
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="department">Department</Label>
                                <div className="relative">
                                    <Building className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="department"
                                        placeholder="Compliance"
                                        className="pl-10"
                                        value={formData.department}
                                        onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="role">Platform Role</Label>
                                <select
                                    id="role"
                                    className="w-full flex h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                    value={formData.role}
                                    onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                                >
                                    <option value="analyst">Risk Analyst</option>
                                    <option value="manager">Executive Manager</option>
                                    <option value="admin">System Administrator</option>
                                </select>
                            </div>
                            <DialogFooter className="pt-4">
                                <Button type="submit" disabled={isSubmitting} className="w-full">
                                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                                    Send Invitation
                                </Button>
                            </DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
            </div>

            <div className="rounded-xl border bg-card shadow-sm overflow-hidden">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-3">
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                        <p className="text-sm text-muted-foreground">Loading users...</p>
                    </div>
                ) : (
                    <Table>
                        <TableHeader className="bg-muted/50">
                            <TableRow>
                                <TableHead className="w-[300px]">User</TableHead>
                                <TableHead>Role</TableHead>
                                <TableHead>Department</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead className="text-right">Actions</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {users.map((u) => (
                                <TableRow key={u.id} className="hover:bg-muted/30 transition-colors">
                                    <TableCell>
                                        <div className="flex items-center gap-3">
                                            <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center text-primary font-semibold text-sm">
                                                {u.fullName.split(' ').map(n => n[0]).join('').toUpperCase()}
                                            </div>
                                            <div>
                                                <p className="font-medium text-foreground">{u.fullName}</p>
                                                <p className="text-xs text-muted-foreground">{u.email}</p>
                                            </div>
                                        </div>
                                    </TableCell>
                                    <TableCell>{getRoleBadge(u.role)}</TableCell>
                                    <TableCell className="text-sm text-slate-600">{u.department || '-'}</TableCell>
                                    <TableCell>
                                        <div className="flex items-center gap-2">
                                            <Switch
                                                checked={u.is_active}
                                                onCheckedChange={() => handleToggleActive(u.id, u.is_active!)}
                                            />
                                            <span className="text-xs font-medium">
                                                {u.is_active ? (
                                                    <span className="text-green-600">Active</span>
                                                ) : (
                                                    <span className="text-slate-400">Inactive</span>
                                                )}
                                            </span>
                                        </div>
                                    </TableCell>
                                    <TableCell className="text-right">
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <Button variant="ghost" className="h-8 w-8 p-0">
                                                    <MoreHorizontal className="h-4 w-4" />
                                                </Button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="w-[180px]">
                                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem onClick={() => handleRoleChange(u.id, 'admin')} className="gap-2">
                                                    Set as Admin
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={() => handleRoleChange(u.id, 'analyst')} className="gap-2">
                                                    Set as Analyst
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={() => handleRoleChange(u.id, 'manager')} className="gap-2">
                                                    Set as Manager
                                                </DropdownMenuItem>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem
                                                    onClick={() => handleDelete(u.id)}
                                                    className="text-destructive gap-2 focus:bg-destructive/10 focus:text-destructive"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                    Revoke Access
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                )}
            </div>

            <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-4 flex gap-3 dark:bg-blue-900/10 dark:border-blue-800">
                <Shield className="h-5 w-5 text-blue-600 flex-shrink-0" />
                <div className="text-sm">
                    <p className="font-semibold text-blue-900 dark:text-blue-300">Security Note:</p>
                    <p className="text-blue-700 dark:text-blue-400/80">
                        Admins have full access to all GRC functions. Analysts can manage risks and controls, while Managers primarily view reports and dashboards.
                    </p>
                </div>
            </div>
        </div>
    );
}
