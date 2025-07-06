export async function GET(request: Request) {
  // For example, fetch data from your DB here
  const secondaryLabels = [ "fem", "L4440", "Q37-YFP"  ];
  return new Response(JSON.stringify(secondaryLabels), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}