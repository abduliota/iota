import { useState, useEffect } from 'react';

const AUTH_STORAGE_KEY = 'ksa_regtech_auth';
const CREDENTIAL_STORAGE_KEY = 'ksa_regtech_credential';

interface AuthUser {
  email: string;
  credentialId: string;
  authenticatedAt: number;
}

export function useFingerprintAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = () => {
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    const authData = localStorage.getItem(AUTH_STORAGE_KEY);
    if (authData) {
      try {
        const user = JSON.parse(authData);
        setUser(user);
        setIsAuthenticated(true);
      } catch {
        setIsAuthenticated(false);
      }
    }
    setIsLoading(false);
  };

  const register = async (email: string): Promise<{ success: boolean; error?: string }> => {
    if (!window.PublicKeyCredential) {
      return { success: false, error: 'WebAuthn not supported in this browser' };
    }

    try {
      const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        rp: {
          name: 'KSA RegTech',
          id: window.location.hostname,
        },
        user: {
          id: new TextEncoder().encode(email),
          name: email,
          displayName: email,
        },
        pubKeyCredParams: [{ alg: -7, type: 'public-key' }],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'required',
        },
        timeout: 60000,
        attestation: 'direct',
      };

      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      }) as PublicKeyCredential;

      if (credential) {
        const authUser: AuthUser = {
          email,
          credentialId: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
          authenticatedAt: Date.now(),
        };

        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        localStorage.setItem(CREDENTIAL_STORAGE_KEY, JSON.stringify({
          id: credential.id,
          rawId: Array.from(new Uint8Array(credential.rawId)),
        }));

        setUser(authUser);
        setIsAuthenticated(true);
        return { success: true };
      }

      return { success: false, error: 'Registration failed' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Registration failed' };
    }
  };

  const login = async (email: string): Promise<{ success: boolean; error?: string }> => {
    if (!window.PublicKeyCredential) {
      return { success: false, error: 'WebAuthn not supported in this browser' };
    }

    try {
      const storedCredential = localStorage.getItem(CREDENTIAL_STORAGE_KEY);
      if (!storedCredential) {
        return { success: false, error: 'No credential found. Please sign up first.' };
      }

      const credentialData = JSON.parse(storedCredential);
      const credentialId = Uint8Array.from(credentialData.rawId);

      const publicKeyCredentialRequestOptions: PublicKeyCredentialRequestOptions = {
        challenge: crypto.getRandomValues(new Uint8Array(32)),
        allowCredentials: [{
          id: credentialId,
          type: 'public-key',
          transports: ['internal'],
        }],
        timeout: 60000,
        userVerification: 'required',
      };

      const assertion = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      }) as PublicKeyCredential;

      if (assertion) {
        const authUser: AuthUser = {
          email,
          credentialId: btoa(String.fromCharCode(...new Uint8Array(assertion.rawId))),
          authenticatedAt: Date.now(),
        };

        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authUser));
        setUser(authUser);
        setIsAuthenticated(true);
        return { success: true };
      }

      return { success: false, error: 'Authentication failed' };
    } catch (error: any) {
      return { success: false, error: error.message || 'Authentication failed' };
    }
  };

  const logout = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(CREDENTIAL_STORAGE_KEY);
    setUser(null);
    setIsAuthenticated(false);
  };

  return { isAuthenticated, user, isLoading, register, login, logout };
}
