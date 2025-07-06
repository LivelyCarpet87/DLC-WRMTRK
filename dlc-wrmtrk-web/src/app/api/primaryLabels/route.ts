

export async function GET(request: Request) {
  // For example, fetch data from your DB here
  const primaryLabels = [ "SEC_72", "SEC_74", "SEC_76"  ];
  return new Response(JSON.stringify(primaryLabels), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}